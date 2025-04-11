import streamlit as st
import fitz  # PyMuPDF
import re
import pandas as pd
import io

st.set_page_config(page_title="HelioScope Report Extractor", layout="wide")
st.title("📄 HelioScope Full PDF Report Extractor")

uploaded_file = st.file_uploader("Upload your HelioScope summary report PDF", type="pdf")

def extract_text(pdf_file):
    pdf_bytes = pdf_file.read()
    pdf_stream = io.BytesIO(pdf_bytes)
    doc = fitz.open(stream=pdf_stream, filetype="pdf")
    return "\n".join([page.get_text() for page in doc])

def extract_data(text):
    data = {}

    # Project Info
    project_name = re.search(r"Project Name\s+(.*)", text)
    address = re.search(r"Project\s+Address\s+(.*?)\s+USA", text, re.DOTALL)
    if project_name: data["Project Name"] = project_name.group(1).strip()
    if address: data["Project Address"] = address.group(1).replace('\n', ', ').strip()

    # Production Info
    production = re.search(r"Annual\s+Production\s+([\d.]+)\s+MWh", text)
    ratio = re.search(r"Performance\s+Ratio\s+([\d.]+)%", text)
    if production: data["Annual Production (MWh)"] = production.group(1)
    if ratio: data["Performance Ratio (%)"] = ratio.group(1)

    # Inverters
    inverters = re.findall(r"Inverters\s+(.*?)\s+\((.*?)\)\s+(\d+) \(([\d.]+) kW\)", text)

    # Strings
    strings = re.findall(r"Strings.*?(\d+)\s+\(([\d,.\s]+) ft\)", text)

    # Modules
    modules = re.findall(r"Module\s+(.*?)\s+(\d+)\s+\(([\d.]+) kW\)", text)

    # Weather
    weather = re.search(r"Weather Dataset\s+(.+?)\s+Simulator Version", text, re.DOTALL)
    if weather: data["Weather Dataset"] = weather.group(1).replace("\n", " ").strip()

    # System Loss
    losses = re.findall(r"(\w+)\s*:\s*([\d.]+)%", text)

    # Monthly Production Table
    month_table = re.findall(
        r"(\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.,]+)\s+([\d.,]+)",
        text
    )

    # Field Segment Layouts
    segment_pattern = re.findall(
        r"Field\s+Segment\s+\d+\s+.*?\nFixed\s+Tilt.*?Module:\s+(\d+)°.*?Module:\s+(\d+)°.*?\n.*?(\d+\.\d+)\s*ft\s+(\d+x\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+kW",
        text, re.DOTALL
    )

        # Enhanced Components Table Parsing: Inverters, Strings, Modules
    components = []
    component_block = re.findall(
        r"(Inverters|Strings[^\n]*?|Module)\s+([A-Za-z0-9\-/,().\s]+?)\s+(\d+)\s+\(([\d.,]+)\s*(kW|ft)\)",
        text
    )
    for comp in component_block:
        components.append({
            "Component": comp[0].strip(),
            "Description": comp[1].strip(),
            "Count": comp[2].strip(),
            "Value": comp[3].strip(),
            "Unit": comp[4].strip()
        })

    # Separate specific data from the components list (optional)
    inverters = [c for c in components if "inverter" in c["Component"].lower()]
    strings = [c for c in components if "string" in c["Component"].lower()]
    modules = [c for c in components if "module" in c["Component"].lower()]


    return data, inverters, strings, modules, losses, month_table, segment_pattern, components


if uploaded_file:
    with st.spinner("⏳ Extracting data..."):
        text = extract_text(uploaded_file)
        proj_data, inverters, strings, modules, losses, monthly, segments, components = extract_data(text)

    st.success("✅ Data extraction complete!")

    st.header("📍 Project Information")
    for k, v in proj_data.items():
        st.write(f"**{k}:** {v}")

    if inverters:
        st.header("🔌 Inverter Information")
        for inv in inverters:
            st.write(f"**Description:** {inv['Description']}")
            st.write(f"**Count:** {inv['Count']}, **Capacity:** {inv['Value']} {inv['Unit']}")
            st.markdown("---")

    if strings:
        st.header("🔗 Strings Information")
        for s in strings:
            st.write(f"**Description:** {s['Description']}")
            st.write(f"**Count:** {s['Count']}, **Length:** {s['Value']} {s['Unit']}")
            st.markdown("---")

    if modules:
        st.header("📦 Module Information")
        for mod in modules:
            st.write(f"**Description:** {mod['Description']}")
            st.write(f"**Count:** {mod['Count']}, **Capacity:** {mod['Value']} {mod['Unit']}")
            st.markdown("---")

    if losses:
        st.header("⚡ System Losses")
        loss_df = pd.DataFrame(losses, columns=["Loss Type", "Loss (%)"])
        st.dataframe(loss_df)

    if monthly:
        st.header("📅 Monthly Energy Production")
        df = pd.DataFrame(monthly, columns=["Month", "GHI", "POA", "Shaded", "Nameplate (kWh)", "Grid (kWh)"])
        st.dataframe(df)

    if segments:
        st.header("🧮 Field Segment Layouts")
        seg_df = pd.DataFrame(segments, columns=[
            "Module Tilt (°)", "Module Azimuth (°)", "Spacing (ft)", "Frame Size",
            "Frames", "Modules", "Power (kW)"
        ])
        st.dataframe(seg_df)

    if components:
        st.header("🧩 Components Table (Full Descriptions)")
        comp_df = pd.DataFrame(components)
        st.dataframe(comp_df)

else:
    st.info("📥 Please upload a HelioScope PDF to begin extraction.")
