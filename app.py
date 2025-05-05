import streamlit as st
import pandas as pd
import openai
import os

# Set up OpenAI API key
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Load static product data (this will be used as a fallback)
base_df = pd.read_csv("Base.csv")
apparel_df = pd.read_csv("Apparel.csv")
construction_df = pd.read_csv("Construction.csv")
energy_df = pd.read_csv("Energy.csv")
hospitality_df = pd.read_csv("Hospitality.csv")
transportation_df = pd.read_csv("Transportation.csv")

industry_dfs = {
    "Apparel": apparel_df,
    "Construction": construction_df,
    "Energy": energy_df,
    "Hospitality": hospitality_df,
    "Transportation": transportation_df
}

# Check if Salesforce-uploaded CSV exists
uploaded_csv_path = "uploaded_from_salesforce.csv"
uploaded_df = None

if os.path.exists(uploaded_csv_path):
    uploaded_df = pd.read_csv(uploaded_csv_path)
    st.sidebar.success("Salesforce data loaded successfully.")
    st.sidebar.dataframe(uploaded_df.head())
else:
    st.sidebar.warning("No Salesforce data received yet.")

def get_recommendation(product_name, industry):
    # Check for the product in base data
    base_product = base_df[base_df["Base Name"] == product_name]
    if base_product.empty:
        return None

    # Extract details from base data
    base_code = base_product["Base Code"].values[0]
    base_moq = base_product["Minimum Order Quantity"].values[0]
    base_terms = base_product["Payment Terms"].values[0]

    reco_product = product_name
    reco_code = base_code
    moq = base_moq
    terms = base_terms

    # If the industry is found, match with the respective data
    if industry in industry_dfs:
        df = industry_dfs[industry]
        match = df[df[df.columns[0]].str.startswith(product_name)]
        if not match.empty:
            reco_product = match[match.columns[0]].values[0]
            reco_code = match[match.columns[1]].values[0]
            moq = match["Minimum Order Quantity"].values[0]
            terms = match["Payment Terms"].values[0]

    return {
        "Product": product_name,
        "Industry": industry,
        "Recommended Product": reco_product,
        "Recommended Code": reco_code,
        "MOQ": int(moq),
        "Payment Terms": terms
    }

def get_deal_insights(product, industry, moq, payment_terms):
    prompt = f"""
    Product: {product}
    Industry: {industry}
    Recommended Product: {product}-{industry[0].upper()}
    Minimum Order Quantity: {moq}
    Payment Terms: {payment_terms}

    Based on this context, answer the following:

    1. What is the probability (0-100%) of closing this deal?
    2. What is the profitability rating? (Low / Medium / High)
    3. What should be the next best step for the sales rep to close this deal?

    Format the response as:
    Deal Probability: <percent>
    Profitability: <rating>
    Next Step: <action>
    """

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

# Streamlit UI
st.title("Product Recommendation Engine")

# Allow user to choose product and industry from static data
selected_product = st.selectbox("Select a Product", base_df["Base Name"].unique())
selected_industry = st.radio("Select Industry", list(industry_dfs.keys()))

# Check if Salesforce-uploaded data exists
if uploaded_df is not None:
    st.subheader("Salesforce Product Data")
    selected_uploaded_row = st.selectbox(
        "Select a row from Salesforce data for recommendation",
        uploaded_df.index
    )

    # Get the product and industry from the selected row
    row = uploaded_df.iloc[selected_uploaded_row]
    salesforce_product = row.get("Base Name") or row.get("Product") or ""
    salesforce_industry = row.get("Industry") or ""

    # Provide option to run recommendation based on Salesforce data
    if st.button("Run Recommendation for Salesforce Data"):
        rec = get_recommendation(salesforce_product, salesforce_industry)
        if rec:
            st.subheader("Recommended Product Details")
            st.write(rec)

            with st.spinner("Generating insights..."):
                insights = get_deal_insights(
                    rec["Product"], rec["Industry"], rec["MOQ"], rec["Payment Terms"]
                )
            st.subheader("Deal Insights")
            st.text(insights)
        else:
            st.error("Salesforce product not matched in base data.")

# Allow user to manually run recommendations with static data
if st.button("Recommend"):
    rec = get_recommendation(selected_product, selected_industry)
    if rec:
        st.subheader("Recommended Product Details")
        st.write(rec)

        with st.spinner("Generating insights..."):
            insights = get_deal_insights(
                rec["Product"], rec["Industry"], rec["MOQ"], rec["Payment Terms"]
            )
        st.subheader("Deal Insights")
        st.text(insights)
    else:
        st.error("Product not found in base data.")
