"""Delay propagation through BER turnarounds, Feb-Apr 2026 manual A-CDM app collection.

Input: DS Lab2/final/cleaned_dataset.csv (2,070 turnarounds, 20 days; user confirmed
values were copied from the app without adjustment).

Model (reactionary delay with a minimum turnaround time, MTT):
    outbound_delay = a + b * max(0, inbound_delay - (scheduled_TA - MTT)) + e
The slack (scheduled_TA - MTT) absorbs inbound delay; only the excess propagates.
MTT is estimated per airline segment by grid search on the training period
(21 Feb - 4 Mar) and evaluated on the held-out period (17 - 24 Apr).
"""
import numpy as np
import pandas as pd

SRC = r"C:/Users/amira/Documents/GitHub/Process-Mining---Turnaround-Process/DS Lab2/final/cleaned_dataset.csv"
RNG = np.random.default_rng(20261120)


def load():
    d = pd.read_csv(SRC)
    for c in ["LandingTime", "LandingActualTime", "DepartureTime", "DepartureActualTime"]:
        d[c] = pd.to_datetime(d[c])
    d["inb"] = (d.LandingActualTime - d.LandingTime).dt.total_seconds() / 60
    d["outb"] = (d.DepartureActualTime - d.DepartureTime).dt.total_seconds() / 60
    d["sta"] = (d.DepartureTime - d.LandingTime).dt.total_seconds() / 60
    d["ata"] = (d.DepartureActualTime - d.LandingActualTime).dt.total_seconds() / 60
    n0 = len(d)
    # Exclusion rules: date-rollover / transcription outliers
    bad = (d.ata <= 15) | (d.outb.abs() > 300) | (d.inb.abs() > 300)
    d = d[~bad].copy()
    d["period"] = np.where(d.LandingTime < "2026-04-01", "train", "test")
    print(f"records {n0}, excluded {bad.sum()}, analysed {len(d)}")
    return d


def fit_mtt(t):
    best = None
    for mtt in np.arange(20, 91, 1):
        x = np.clip(t.inb - (t.sta - mtt), 0, None)
        X = np.c_[np.ones(len(x)), x]
        coef, *_ = np.linalg.lstsq(X, t.outb, rcond=None)
        mae = np.abs(X @ coef - t.outb).mean()
        if best is None or mae < best[0]:
            best = (mae, mtt, coef)
    return best


def predict(t, mtt, coef):
    x = np.clip(t.inb - (t.sta - mtt), 0, None)
    return coef[0] + coef[1] * x


def main():
    d = load()
    print(d.groupby(["period", "type"]).size().unstack())
    print("\nDescriptives (min):")
    print(d.groupby("type")[["inb", "outb", "sta", "ata"]].median().round(1))
    r = d[["inb", "outb"]].corr(method="spearman").iloc[0, 1]
    print(f"Spearman(inbound delay, outbound delay) all = {r:.2f}")

    tr, te = d[d.period == "train"], d[d.period == "test"]
    rows = []
    for seg in ["full", "low-cost"]:
        a, b = tr[tr.type == seg], te[te.type == seg]
        mae_tr, mtt, coef = fit_mtt(a)
        # bootstrap MTT on training data
        boots = []
        for _ in range(300):
            s = a.sample(len(a), replace=True, random_state=int(RNG.integers(1e9)))
            boots.append(fit_mtt(s)[1])
        lo, hi = np.percentile(boots, [2.5, 97.5])
        p = predict(b, mtt, coef)
        mae_model = np.abs(p - b.outb).mean()
        mae_carry = np.abs(b.inb - b.outb).mean()          # naive: delay fully carried
        mae_const = np.abs(a.outb.median() - b.outb).mean()  # naive: constant median
        prop = b[(b.inb - (b.sta - mtt)) > 0]
        rows.append(dict(segment=seg, n_train=len(a), n_test=len(b), MTT=mtt,
                         MTT_CI=f"[{lo:.0f}, {hi:.0f}]", intercept=round(coef[0], 1),
                         slope=round(coef[1], 2), MAE_test_model=round(mae_model, 1),
                         MAE_test_carry=round(mae_carry, 1),
                         MAE_test_const=round(mae_const, 1),
                         share_test_slack_exceeded=round(len(prop) / len(b), 3)))
    res = pd.DataFrame(rows)
    print("\nHeld-out evaluation (train Feb-Mar, test Apr):")
    print(res.to_string(index=False))

    # stand/gate area descriptive
    d["area"] = d.Gate.astype(str).str[0]
    print("\nGate area medians:")
    print(d.groupby("area")[["inb", "outb", "sta", "ata"]].median().round(1)
          .join(d.area.value_counts().rename("n")))

    # binned propagation curve (for figure)
    d["slack"] = d.sta - d.groupby("type").ata.transform(lambda s: s.quantile(.05))
    d["excess"] = d.inb - (d.sta - 40)
    d["bin"] = pd.cut(d.excess, [-400, -60, -30, -15, 0, 15, 30, 60, 300])
    print("\nOutbound delay by inbound excess over (STA - 40 min):")
    print(d.groupby("bin", observed=True).outb.agg(["count", "median", "mean"]).round(1))


if __name__ == "__main__":
    main()
