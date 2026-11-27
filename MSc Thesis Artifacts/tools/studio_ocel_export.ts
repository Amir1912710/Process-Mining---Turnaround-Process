// Adapted verbatim from ELTE-DSED/ocpn-studio src/components/SimulationPanel.tsx.
// Copyright original contributors; MIT license. Retrieved 2026-11-13.
// Type-only import for source compatibility.
type SimulationEvent = any;
// OCEL 2.0 Types
interface OCEL2ObjectType {
  name: string;
  attributes: { name: string; type: string }[];
}

interface OCEL2EventType {
  name: string;
  attributes: { name: string; type: string }[];
}

interface OCEL2Object {
  id: string;
  type: string;
  attributes: { name: string; time: string; value: string }[];
  relationships: { objectId: string; qualifier: string }[];
}

interface OCEL2Event {
  id: string;
  type: string;
  time: string;
  attributes: { name: string; value: string }[];
  relationships: { objectId: string; qualifier: string }[];
}

interface OCEL2Export {
  objectTypes: OCEL2ObjectType[];
  eventTypes: OCEL2EventType[];
  objects: OCEL2Object[];
  events: OCEL2Event[];
}

/**
 * Unwrap a timed token wrapper ({value, timestamp}) if present.
 * WASM tokens store timestamps separately, but some paths may still wrap them.
 */
function unwrapTimedToken(token: unknown): unknown {
  if (token && typeof token === 'object' && !Array.isArray(token)) {
    const obj = token as Record<string, unknown>;
    if ('value' in obj && 'timestamp' in obj) {
      return obj.value;
    }
  }
  return token;
}

/**
 * Format an attribute value for OCEL 2.0.
 * Avoids producing "[object Object]" for nested values.
 */
function formatAttributeValue(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

/**
 * Generate a stable object ID from a record token using its 'id'/'ID' field.
 * Falls back to a content hash if no id field is present.
 */
function stableObjectId(token: unknown, typeName: string): string {
  const typePrefix = typeName.toLowerCase();
  const unwrapped = unwrapTimedToken(token);
  if (unwrapped && typeof unwrapped === 'object' && !Array.isArray(unwrapped)) {
    const record = unwrapped as Record<string, unknown>;
    if ('id' in record) return `${typePrefix}_${record.id}`;
    if ('ID' in record) return `${typePrefix}_${record.ID}`;
  }
  // Fallback: content hash
  const hash = JSON.stringify(unwrapped).split('').reduce((a, b) => {
    a = ((a << 5) - a) + b.charCodeAt(0);
    return a & a;
  }, 0);
  return `${typePrefix}_${Math.abs(hash)}`;
}

/**
 * Parse product color set definitions to extract component record type names.
 * e.g., "colset AircraftxGate = product Aircraft * Gate timed;" → ["Aircraft", "Gate"]
 */
function parseProductComponents(
  colorSets: { name: string; type: string; definition: string }[]
): Map<string, string[]> {
  const result = new Map<string, string[]>();
  for (const cs of colorSets) {
    if (cs.type !== 'product') continue;
    const match = cs.definition.match(/=\s*product\s+(.+?)(?:\s+timed)?;/);
    if (match) {
      const components = match[1].split('*').map(s => s.trim());
      result.set(cs.name, components);
    }
  }
  return result;
}

/**
 * Convert simulation events and model data to OCEL 2.0 format.
 *
 * Handles:
 * - Record color sets: tokens are objects with fields (id, name, etc.)
 * - Product color sets: tokens are arrays of component record objects
 * - Stable object identity based on record type + id field
 * - Proper attribute serialization (no "[object Object]")
 */
/**
 * A reference carried by a record field, from which the export derives a qualified
 * OCEL object-to-object relationship. Structural references (a field that embeds
 * another record, directly or as a list) are detected from the colorset definitions;
 * plain id-typed fields become references via the colorset's `refs` annotations.
 */
interface O2ORefSpec {
  field: string; // Field name as it appears in tokens
  target: string; // Referenced object type (record colorset name)
  qualifier: string; // o2o qualifier (object → object)
  eventQualifier: string; // e2o qualifier: role of objects reached through this field
  reverse: boolean; // Emit target→owner instead of owner→target
  embedded: boolean; // Field embeds record token(s) rather than carrying plain id(s)
}

/** "colset Items = list Item;" → "Item" */
function parseListElementName(definition: string): string | null {
  const m = definition.match(/=\s*list\s+(\w+)/);
  return m ? m[1] : null;
}

function convertToOCEL2(
  events: SimulationEvent[],
  colorSets: { name: string; type: string; definition: string; refs?: { field: string; target: string; qualifier?: string; reverse?: boolean; eventQualifier?: string }[] }[],
  transitions: { id: string; name: string }[],
  places: { id: string; name: string; colorSet: string }[],
  simulationEpoch: string | null,
  arcs: { source: string; target: string; qualifier?: string; isBidirectional?: boolean }[] = [],
  /**
   * Which transitions are exported as events. Undefined exports all of them.
   *
   * Deliberately passed in rather than applied by pre-filtering `events`: objects, their
   * attribute history and their o2o relations are derived from *every* firing, because a
   * transition being scaffolding rather than a business activity says nothing about the
   * objects it moved. Pre-filtering instead loses every object that only a scaffolding
   * transition ever touches — in the order-management model that is all 20 Products,
   * taking the `product` role and the price history with them.
   */
  includedTransitionIds?: Set<string>
): OCEL2Export {
  // --- Build ObjectTypes and reference specs from Record ColorSets ---
  const objectTypes: OCEL2ObjectType[] = [];
  const recordColorSets = colorSets.filter(cs => cs.type === 'record');
  const recordColorSetNames = new Set(recordColorSets.map(cs => cs.name));
  const refSpecsByType = new Map<string, O2ORefSpec[]>();

  for (const cs of recordColorSets) {
    // Parse record fields: "colset X = record id: INT * name: STRING timed;"
    const fields: { name: string; type: string }[] = [];
    const recordMatch = cs.definition.match(/=\s*record\s+(.+?)(?:\s+timed)?;/);
    if (recordMatch) {
      for (const field of recordMatch[1].split('*').map(f => f.trim())) {
        const [name, type] = field.split(':').map(s => s.trim());
        if (name && type) fields.push({ name, type });
      }
    }

    // Derive reference specs: structural (field type resolves to a record colorset,
    // directly or through a list) or annotated (plain id-typed field with a `refs` entry)
    const annotations = new Map((cs.refs ?? []).map(r => [r.field, r]));
    const specs: O2ORefSpec[] = [];
    for (const { name: fieldName, type: fieldType } of fields) {
      let structuralTarget: string | null = null;
      if (recordColorSetNames.has(fieldType)) {
        structuralTarget = fieldType;
      } else {
        const listCs = colorSets.find(c => c.name === fieldType && c.type === 'list');
        const element = listCs ? parseListElementName(listCs.definition) : null;
        if (element && recordColorSetNames.has(element)) structuralTarget = element;
      }
      const ann = annotations.get(fieldName);
      if (structuralTarget || ann?.target) {
        const qualifier = ann?.qualifier ?? fieldName.toLowerCase();
        specs.push({
          field: fieldName,
          target: structuralTarget ?? ann!.target,
          qualifier,
          eventQualifier: ann?.eventQualifier ?? qualifier,
          reverse: ann?.reverse ?? false,
          embedded: !!structuralTarget,
        });
      }
    }
    if (specs.length > 0) refSpecsByType.set(cs.name, specs);

    // Reference fields are exported as o2o relationships, not attributes
    const refFieldNames = new Set(specs.map(s => s.field.toLowerCase()));
    const attributes = fields
      .filter(f => f.name.toLowerCase() !== 'id' && !refFieldNames.has(f.name.toLowerCase()))
      .map(f => ({ name: f.name.toLowerCase(), type: f.type.toLowerCase() }));
    objectTypes.push({ name: cs.name, attributes });
  }

  // --- Parse product color sets → component types ---
  const productComponentsMap = parseProductComponents(colorSets);

  // --- Build EventTypes from the transitions that are exported as events ---
  const isExported = (transitionId: string) =>
    !includedTransitionIds || includedTransitionIds.has(transitionId);
  const eventTypes: OCEL2EventType[] = transitions
    .filter(t => isExported(t.id))
    .map(t => ({
      name: t.name || t.id,
      attributes: [],
    }));

  // --- Build place ID → ColorSet name map ---
  const placeColorSetMap = new Map<string, string>();
  for (const place of places) {
    placeColorSetMap.set(place.id, place.colorSet);
  }

  // --- Build arc role qualifier lookup: (transition, place, direction) → qualifier ---
  // An object's role in an event follows from how the transition touches it, which
  // structurally is the arc: an input arc and an output arc on the same place are
  // different roles (e.g. "shipped package" vs "creates").
  const placeIds = new Set(places.map(p => p.id));
  const transitionIds = new Set(transitions.map(t => t.id));
  const arcQualifierByKey = new Map<string, string>();
  for (const arc of arcs) {
    const qualifier = arc.qualifier?.trim();
    if (!qualifier) continue;
    let placeId: string;
    let transitionId: string;
    let direction: 'in' | 'out';
    if (placeIds.has(arc.source) && transitionIds.has(arc.target)) {
      placeId = arc.source;
      transitionId = arc.target;
      direction = 'in';
    } else if (transitionIds.has(arc.source) && placeIds.has(arc.target)) {
      transitionId = arc.source;
      placeId = arc.target;
      direction = 'out';
    } else {
      continue; // not a place↔transition arc (e.g. it targets a substitution transition)
    }
    arcQualifierByKey.set(`${transitionId}|${placeId}|${direction}`, qualifier);
    if (arc.isBidirectional) {
      // A bidirectional arc both consumes and produces, in the same role
      arcQualifierByKey.set(`${transitionId}|${placeId}|${direction === 'in' ? 'out' : 'in'}`, qualifier);
    }
  }

  // --- Track unique objects and their evolving attribute state ---
  const objectsMap = new Map<string, OCEL2Object>();
  // Last known formatted attribute values per object, used to detect changes
  const objectAttrState = new Map<string, Map<string, string>>();

  const epochDate = simulationEpoch ? new Date(simulationEpoch) : null;
  // Simulation time zero, used to stamp initial attribute values of objects that
  // pre-exist the log (first seen in consumed tokens, i.e. from the initial marking).
  // Without an explicit epoch it is derived from the first event's wall-clock
  // timestamp minus its elapsed simulation time.
  const timeZeroISO = epochDate
    ? epochDate.toISOString()
    : events.length > 0
      ? new Date(events[0].timestamp.getTime() - events[0].time).toISOString()
      : null;

  /**
   * Extract a record token's attribute values, formatted. Excludes the id field
   * (it is the object identifier) and reference fields (they are exported as o2o
   * relationships, not attributes).
   */
  function extractAttributes(unwrapped: unknown, excludeFields?: Set<string>): Map<string, string> {
    const attrs = new Map<string, string>();
    if (unwrapped && typeof unwrapped === 'object' && !Array.isArray(unwrapped)) {
      for (const [key, value] of Object.entries(unwrapped as Record<string, unknown>)) {
        const lower = key.toLowerCase();
        if (lower === 'id') continue; // id is the object identifier, not an attribute
        if (excludeFields?.has(lower)) continue;
        attrs.set(lower, formatAttributeValue(value));
      }
    }
    return attrs;
  }

  // Derived o2o relationship candidates, resolved and deduped after the event loop
  // (a reference may point at an object that is only registered by a later event)
  const pendingRelations: Array<{ source: string; target: string; qualifier: string }> = [];

  /**
   * Register a record object occurrence and track attribute changes.
   * Returns the stable objectId.
   *
   * Timed-CPN semantics: a firing is atomic, so state produced by an event exists
   * from the event's time onward — token availability delays play no role here.
   * - First seen in consumed tokens → the object pre-existed the event (initial
   *   marking): its attributes are initial values, stamped at simulation time zero.
   * - First seen in produced tokens → created by this event: initial values are
   *   stamped at the event's time.
   * - Produced with attribute values differing from the last known state → a
   *   change entry per differing attribute, stamped at the event's time.
   */
  function registerObject(
    token: unknown,
    typeName: string,
    eventTime: string,
    produced: boolean,
    role: string | null,
    involved: Map<string, { objectId: string; qualifier: string }>
  ): string {
    const unwrapped = unwrapTimedToken(token);
    const objectId = stableObjectId(unwrapped, typeName);
    const refSpecs = refSpecsByType.get(typeName);
    const refFieldNames = refSpecs && new Set(refSpecs.map(s => s.field.toLowerCase()));
    const attrs = extractAttributes(unwrapped, refFieldNames || undefined);

    // The role this object plays in the current event. An object can legitimately
    // play more than one role (OCEL 2.0 keys e2o on the event/object/qualifier
    // triple), so entries are deduped on the object-plus-qualifier pair.
    const qualifier = role || typeName.toLowerCase();
    involved.set(`${objectId}|${qualifier}`, { objectId, qualifier });

    const existing = objectsMap.get(objectId);
    if (!existing) {
      const initialTime = produced ? eventTime : (timeZeroISO ?? eventTime);
      objectsMap.set(objectId, {
        id: objectId,
        type: typeName,
        attributes: Array.from(attrs, ([name, value]) => ({ name, time: initialTime, value })),
        relationships: [],
      });
      objectAttrState.set(objectId, attrs);
    } else if (produced) {
      // Only produced tokens carry post-firing state; consumed tokens hold the
      // pre-firing state and can never introduce a change.
      const state = objectAttrState.get(objectId)!;
      for (const [name, value] of attrs) {
        if (state.get(name) !== value) {
          existing.attributes.push({ name, time: eventTime, value });
          state.set(name, value);
        }
      }
    }

    // --- Derive o2o relationships from reference fields of this token state ---
    // Relationships are cumulative in OCEL 2.0 (no time dimension), so every
    // occurrence contributes and duplicates are dropped at the end.
    if (refSpecs && unwrapped && typeof unwrapped === 'object' && !Array.isArray(unwrapped)) {
      const record = unwrapped as Record<string, unknown>;
      for (const spec of refSpecs) {
        const raw = record[spec.field] ?? record[spec.field.toLowerCase()];
        if (raw === null || raw === undefined || raw === '') continue;
        const elements = Array.isArray(raw) ? raw : [raw];
        for (const element of elements) {
          let targetId: string | null = null;
          if (spec.embedded) {
            // The field embeds the referenced object's token — register it too;
            // it is genuinely part of the state. Its role in this event comes from
            // the field it was reached through, not from the arc.
            const inner = unwrapTimedToken(element);
            if (inner && typeof inner === 'object') {
              targetId = registerObject(element, spec.target, eventTime, produced, spec.eventQualifier, involved);
            }
          } else if (typeof element === 'string' || typeof element === 'number') {
            // The field carries the referenced object's id. The object itself is not
            // part of this token, but the event does touch it through the reference;
            // dangling ids are filtered out once all objects are known.
            targetId = `${spec.target.toLowerCase()}_${element}`;
            involved.set(`${targetId}|${spec.eventQualifier}`, {
              objectId: targetId,
              qualifier: spec.eventQualifier,
            });
          }
          if (targetId && targetId !== objectId) {
            pendingRelations.push(
              spec.reverse
                ? { source: targetId, target: objectId, qualifier: spec.qualifier }
                : { source: objectId, target: targetId, qualifier: spec.qualifier }
            );
          }
        }
      }
    }

    return objectId;
  }

  /**
   * Process a token from a place, potentially decomposing product tokens
   * into individual record objects, recording each in `involved` with the role
   * it plays in the current event.
   *
   * `arcQualifier` is the role declared on the arc that moved this token. It applies
   * to the objects the arc carries directly; objects reached through reference fields
   * take their role from the field instead (see registerObject). Product components
   * all share the arc's qualifier — a product has no field names to tell its
   * components apart, which is a reason to prefer records for object types.
   */
  function processToken(
    token: unknown,
    colorSetName: string,
    eventTime: string,
    produced: boolean,
    arcQualifier: string | null,
    involved: Map<string, { objectId: string; qualifier: string }>
  ): void {
    if (recordColorSetNames.has(colorSetName)) {
      // Direct record type — register the token as an object
      registerObject(token, colorSetName, eventTime, produced, arcQualifier, involved);
    } else if (productComponentsMap.has(colorSetName)) {
      // Product type — decompose into component record objects
      const componentTypes = productComponentsMap.get(colorSetName)!;
      const unwrapped = unwrapTimedToken(token);

      if (Array.isArray(unwrapped) && unwrapped.length === componentTypes.length) {
        for (let i = 0; i < componentTypes.length; i++) {
          const compType = componentTypes[i];
          if (recordColorSetNames.has(compType)) {
            registerObject(unwrapped[i], compType, eventTime, produced, arcQualifier, involved);
          }
        }
      }
    }
  }

  // --- Build OCEL Events ---
  const ocelEvents: OCEL2Event[] = [];

  for (const event of events) {
    const eventId = `e${event.step}`;
    const eventType = event.transitionName;
    const eventTime = epochDate
      ? new Date(epochDate.getTime() + event.time).toISOString()
      : event.timestamp.toISOString();

    // Objects involved in this event, keyed by object-plus-qualifier so one object
    // can hold several roles
    const involvedObjects = new Map<string, { objectId: string; qualifier: string }>();

    // Process consumed tokens (pre-firing state) before produced tokens
    // (post-firing state) so attribute changes are diffed in firing order
    const allTokenMovements = [
      ...event.tokens.consumed.map((movement) => ({ movement, produced: false })),
      ...event.tokens.produced.map((movement) => ({ movement, produced: true })),
    ];

    for (const { movement, produced } of allTokenMovements) {
      const colorSetName = placeColorSetMap.get(movement.placeId);
      if (!colorSetName) continue;

      // Only process record and product types (skip UNIT, INT, STRING, etc.)
      const isRelevant =
        recordColorSetNames.has(colorSetName) ||
        productComponentsMap.has(colorSetName);
      if (!isRelevant) continue;

      // The arc that moved these tokens declares the role they play. Firing events
      // identify token movements by place, so the arc is resolved by
      // (transition, place, direction) — unique except for parallel arcs, which
      // validation flags when they disagree.
      const arcQualifier = arcQualifierByKey.get(
        `${event.transitionId}|${movement.placeId}|${produced ? 'out' : 'in'}`
      ) ?? null;

      try {
        const tokens = JSON.parse(movement.tokens);
        if (Array.isArray(tokens)) {
          for (const token of tokens) {
            processToken(token, colorSetName, eventTime, produced, arcQualifier, involvedObjects);
          }
        }
      } catch {
        // Skip if tokens can't be parsed
      }
    }

    // Every firing above contributed to the objects, their attribute history and their
    // o2o relations; only the exported ones become events. An excluded transition is a
    // statement about the *event* log ("this is scaffolding, not a business activity"),
    // not about the objects it happened to move: in OCEL 2.0 objects exist independently
    // of events, and the reference order-management log is exactly this shape — products
    // carry five price changes each while no `update price` event type exists.
    if (isExported(event.transitionId)) {
      ocelEvents.push({
        id: eventId,
        type: eventType,
        time: eventTime,
        attributes: [],
        relationships: Array.from(involvedObjects.values()),
      });
    }
  }

  // Objects referenced only by id may never appear as a token of their own; drop
  // those e2o relations rather than pointing at objects the log does not contain
  for (const event of ocelEvents) {
    event.relationships = event.relationships.filter(r => objectsMap.has(r.objectId));
  }

  // --- Attach derived o2o relationships (deduped, only between logged objects) ---
  const seenRelations = new Set<string>();
  for (const rel of pendingRelations) {
    const sourceObj = objectsMap.get(rel.source);
    if (!sourceObj || !objectsMap.has(rel.target)) continue;
    const key = `${rel.source}|${rel.target}|${rel.qualifier}`;
    if (seenRelations.has(key)) continue;
    seenRelations.add(key);
    sourceObj.relationships.push({ objectId: rel.target, qualifier: rel.qualifier });
  }

  return {
    objectTypes,
    eventTypes,
    objects: Array.from(objectsMap.values()),
    events: ocelEvents,
  };
}
export { convertToOCEL2 };

