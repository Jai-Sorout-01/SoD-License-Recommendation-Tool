# pip install streamlit pandas openpyxl plotly pillow

import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from PIL import Image

# STREAMLIT PAGE CONFIG
st.set_page_config(page_title="SAP License Recommendation Tool", page_icon= r"https://raw.githubusercontent.com/Jai-Sorout-01/SoD-License-Recommendation-Tool/main/Victora%20Logo.png", layout="wide")

# COMPANY LOGO
logo_path = r"https://raw.githubusercontent.com/Jai-Sorout-01/SoD-License-Recommendation-Tool/main/Victora%20Logo.png"

try:
    logo = Image.open(logo_path)
    st.image(logo, width=200)
except Exception: 
    st.warning("⚠️ Logo not found, continuing without logo.")

st.title("💼 Victora – SAP License Recommendation Tool")

# LICENSE PRIORITY LOGIC

LICENSE_PRIORITY = {"Professional": 3, "Functional": 2, "Productivity": 1}


def normalize_license(license_name):
    """Clean and standardize license names."""
    if pd.isna(license_name):
        return None
    return str(license_name).strip().title()


def get_highest_license(license_list):
    """Return the highest priority license present in the list."""
    license_list = [normalize_license(lic) for lic in license_list if lic]
    valid_licenses = [lic for lic in license_list if lic in LICENSE_PRIORITY]
    if not valid_licenses:
        return "No Data"
    return max(valid_licenses, key=lambda x: LICENSE_PRIORITY[x])


def determine_status(current, recommended):
    current = normalize_license(current)
    recommended = normalize_license(recommended)
    if current == recommended:
        return "✅ Optimized"
    if LICENSE_PRIORITY.get(current, 0) > LICENSE_PRIORITY.get(recommended, 0):
        return "🔻 Over-Licensed"
    if LICENSE_PRIORITY.get(current, 0) < LICENSE_PRIORITY.get(recommended, 0):
        return "⚠️ Under-Licensed"
    return "⚙️ Review"

# SIDEBAR - FILE UPLOAD

st.sidebar.header("📁 Upload Input Files (once)")
user_file = st.sidebar.file_uploader("Upload User–Tcode file", type=["xlsx", "xls"])
license_master_file = st.sidebar.file_uploader("Upload License Master Data", type=["xlsx", "xls"])

# PROCESSING

if user_file and license_master_file:
    df_users = pd.read_excel(user_file)
    df_license_master = pd.read_excel(license_master_file)

    # Clean column names
    df_users.columns = df_users.columns.str.strip()
    df_license_master.columns = df_license_master.columns.str.strip()

    # Ensure Tcode columns exist and are cleaned
    if "Tcode" not in df_users.columns or "Tcode" not in df_license_master.columns:
        st.error("❌ 'Tcode' column missing in one of the files.")
        st.stop()

    # Normalize Tcode for matching
    df_users["Tcode"] = df_users["Tcode"].astype(str).str.strip().str.upper()
    df_license_master["Tcode"] = df_license_master["Tcode"].astype(str).str.strip().str.upper()

    # Normalize License Type
    if "License Type" in df_license_master.columns:
        df_license_master["License Type"] = (
            df_license_master["License Type"].astype(str).str.strip().str.title()
        )
    else:
        st.error("❌ 'License Type' column missing in License Master file.")
        st.stop()

    # Merge both sheets
    merged = pd.merge(df_users, df_license_master, on="Tcode", how="left")

    # Tabs
    tab1, tab2 = st.tabs(["🧍 Manual Mode", "📊 Bulk Mode"])

    # 🧍 MANUAL MODE
   
    with tab1:
        st.header("Manual Mode – Analyze Single User")
        users = merged["User Name"].dropna().unique()
        selected_user = st.selectbox("Select User", users)

        user_data = merged[merged["User Name"] == selected_user]

        # Safe current license extraction
        if "License" in user_data.columns and not user_data["License"].dropna().empty:
            mode_values = user_data["License"].mode()
            current_license = mode_values[0] if not mode_values.empty else "Not Assigned"
        else:
            current_license = "Not Assigned"

        # Determine recommendation
        license_list = [normalize_license(x) for x in user_data["License Type"].dropna().tolist()]
        recommended_license = get_highest_license(license_list)
        status = determine_status(current_license, recommended_license)

        st.markdown(f"### 👤 User: `{selected_user}`")
        st.write(f"**Current License:** {current_license}")
        st.write(f"**Recommended License:** {recommended_license}")
        st.write(f"**Status:** {status}")

        # Pie chart
        chart_data = user_data["License Type"].value_counts().reset_index()
        chart_data.columns = ["License Type", "Count"]
        if not chart_data.empty:
            fig = px.pie(
                chart_data,
                names="License Type",
                values="Count",
                title="User License Type Distribution",
                hole=0.4,
            )
            st.plotly_chart(fig, use_container_width=True)

        # Table
        cols_to_show = [c for c in ["Tcode", "License Type", "Description"] if c in user_data.columns]
        st.dataframe(user_data[cols_to_show].fillna("N/A"), use_container_width=True)

    # 📊 BULK MODE
    
    with tab2:
        st.header("Bulk License Optimization Report")

        user_results = []
        for user, group in merged.groupby("User Name"):
            license_list = [normalize_license(x) for x in group["License Type"].dropna().tolist()]
            recommended_license = get_highest_license(license_list)

            # Safe current license extraction
            if "License" in group.columns and not group["License"].dropna().empty:
                mode_values = group["License"].mode()
                current_license = mode_values[0] if not mode_values.empty else "Not Assigned"
            else:
                current_license = "Not Assigned"

            status = determine_status(current_license, recommended_license)
            user_results.append(
                {
                    "User Name": user,
                    "User ID": group["User ID"].iloc[0] if "User ID" in group.columns else "N/A",
                    "Current License": current_license,
                    "Recommended License": recommended_license,
                    "Status": status,
                }
            )

        df_result = pd.DataFrame(user_results)

        st.success("✅ License Recommendation Report Generated!")
        st.dataframe(df_result, use_container_width=True)

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            license_dist = df_result["Recommended License"].value_counts().reset_index()
            license_dist.columns = ["License Type", "Count"]
            if not license_dist.empty:
                fig1 = px.pie(
                    license_dist,
                    names="License Type",
                    values="Count",
                    title="Recommended License Distribution",
                    hole=0.4,
                )
                st.plotly_chart(fig1, use_container_width=True)

        with col2:
            status_dist = df_result["Status"].value_counts().reset_index()
            status_dist.columns = ["Status", "Count"]
            if not status_dist.empty:
                fig2 = px.bar(
                    status_dist,
                    x="Status",
                    y="Count",
                    title="License Optimization Status",
                    text_auto=True,
                )
                st.plotly_chart(fig2, use_container_width=True)

        # Excel Download
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_result.to_excel(writer, index=False, sheet_name="License Recommendation")
        st.download_button(
            label="⬇️ Download Excel Report",
            data=output.getvalue(),
            file_name="License_Recommendation_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

else:
    st.info("⬅️ Please upload both the **User–Tcode** file and the **License Master** file to continue.")






