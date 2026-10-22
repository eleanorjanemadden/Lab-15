"""Run: python3 -m streamlit run app.py."""
import hashlib
import importlib
import io
from pathlib import Path
import streamlit as st
import portfolio

# Reload the engine so a browser rerun picks up saved training-input changes.
importlib.reload(portfolio)

st.set_page_config(page_title="Portfolio stability", layout="wide")
st.title("Portfolio stability")
st.caption("Built with AI help, a learning demonstration, not investment advice.")
objective = st.sidebar.number_input("Objective (%)", value=6.5, step=0.1) / 100
minimum = st.sidebar.number_input("Reserve minimum (%)", min_value=0.0,
                                  max_value=100.0, value=3.0, step=1.0) / 100
upload = st.sidebar.file_uploader("Upload prices.csv", type="csv")
bundled = st.sidebar.checkbox("Use included Project 2 prices.csv", value=False)
last_36 = st.sidebar.checkbox("Last 36 months", value=False)

try:
    raw = upload.getvalue() if upload is not None else (
        Path(__file__).with_name("prices.csv").read_bytes() if bundled else None)
    if raw is None:
        loaded = {"assets": portfolio.SLEEVES, "returns": portfolio.RETURNS,
                  "volatilities": portfolio.VOLATILITIES,
                  "correlations": portfolio.CORRELATIONS}
        current = loaded
        default_eligible = portfolio.RESERVE_ELIGIBLE
        dataset = "meridian"
        st.write("Meridian — annual course-authored training values")
        if last_36:
            st.info("The 36-month switch applies to CSV prices; Meridian has fixed training inputs.")
    else:
        text = raw.decode("utf-8-sig")
        loaded = portfolio.estimate_from_csv(io.StringIO(text))
        current = portfolio.estimate_from_csv(io.StringIO(text), last_36=last_36)
        default_eligible = [ticker in {"BIL", "IEF"} for ticker in loaded["assets"]]
        dataset = hashlib.sha256(raw).hexdigest()[:12]
        st.write(f"Monthly-price estimates — {current['months']} monthly returns, "
                 f"{current['first_return_month']} through {current['last_return_month']}")
        st.caption("Historical arithmetic estimates, not forecasts. BIL and IEF count for the "
                   "draft mandate; review reserve eligibility for other uploads.")
    st.subheader("Edit annual expected returns and reserve eligibility")
    estimates, eligible = [], []
    for index, asset in enumerate(current["assets"]):
        left, right = st.columns([3, 2])
        # A different window gets its own controls initialized to that window's estimates.
        estimates.append(left.number_input(f"{asset} return estimate (%)",
                         value=current["returns"][index] * 100, step=0.1,
                         key=f"return_{dataset}_{last_36}_{index}") / 100)
        eligible.append(right.checkbox(f"{asset} reserve-eligible",
                        value=default_eligible[index], key=f"reserve_{dataset}_{index}"))

    baseline = portfolio.search_portfolio(loaded["returns"], loaded["volatilities"],
               loaded["correlations"], objective, default_eligible, minimum)
    answer = portfolio.search_portfolio(estimates, current["volatilities"],
             current["correlations"], objective, eligible, minimum)

    def display_result(title, result):
        st.subheader(title)
        if result is None:
            st.warning("no mix meets the objective")
            return
        st.table({"Asset": loaded["assets"],
                  "Weight (%)": [f"{w * 100:.2f}" for w in result["weights"]]})
        st.write(f"Expected return estimate: {result['return']:.2%}")
        st.write(f"Annual volatility: {result['volatility']:.2%}")
        st.write(f"Reserve-eligible weight: {result['reserve']:.2%}")

    left, right = st.columns(2)
    with left:
        display_result("Current lowest-risk mix", answer)
    with right:
        display_result("As loaded — all months", baseline)
    st.caption("Both searches use the current sidebar objective and minimum. As loaded keeps "
               "the original returns, risk estimates and default eligibility.")
    if answer is not None and baseline is not None:
        change = max(abs(a-b) for a, b in zip(answer["weights"], baseline["weights"])) * 100
        st.metric("Largest weight change (percentage points)", f"{change:.2f}")
    else:
        st.info("Largest weight change: N/A when either search has no feasible mix.")
    st.caption("Fully invested, long-only mixes in 5-point steps. Lowest risk means lowest "
               "estimated volatility among these mixes; losses remain possible.")
except (ValueError, UnicodeError, OSError) as error:
    st.error(f"Input error: {error}")
