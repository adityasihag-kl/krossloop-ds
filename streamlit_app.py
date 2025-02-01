import streamlit as st
import time
import uuid
import os
from datetime import datetime

from main import process_AAT, process_COATT_parallel

model_options = ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-exp-1206", "gemini-1.5-pro"]
approach_options = ["One at a time - with Contemplator", "All at once"]
country_options = ["United States of America", "India", "United Kingdom", "Australia", "Germany"]

def save_uploaded_file(uploaded_file, folder = "uploaded_pdfs"):
    """
    Save uploaded file with a unique ID and return the filename
    """
    # Create folder if it doesn't exist
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{timestamp}_{unique_id}_{uploaded_file.name}"
    file_path = os.path.join(folder, filename)
    
    # Save the file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getvalue())
    
    return file_path

def process_pdfs_with_llm(data_source_pdf_path, model, approach, country) -> str:
    """
    Process the PDF files with an LLM.
    Replace this with your actual LLM implementation.
    """
    try:
        if approach == approach_options[0]:
            response = process_COATT_parallel(data_source_pdf_path, model, country)
        elif approach == approach_options[1]:
            response = process_AAT(data_source_pdf_path, model, country)
    except Exception as e:
        response = "Something went wrong.. :/\n"
        response += str(e)
    
    # Return mock response - Replace with actual LLM response
    return response

def main():
    st.title("Data Sources - Suggest Services")

    # Custom CSS to hide the Streamlit toolbar
    st.markdown("""
        <style>
            .stAppToolbar {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # File uploaders
    data_source_pdf = st.file_uploader(
        "Upload Data Source PDF",
        type = ['pdf'],
        accept_multiple_files = False,
        key = "data_source_pdf"
    )

    # Model Selector
    selected_model = st.selectbox("Select Model", options = model_options, index = 0)

    # Approach Selector
    selected_approach = st.selectbox("Select Approach", options = approach_options, index = 0)

    # Country Selector
    selected_country = st.selectbox("Select Country", options = country_options, index = 0)
    
    # GO button
    if data_source_pdf is not None:
        if st.button("GO"):
            with st.spinner("Processing..."):
                # Save files
                data_source_pdf_path = save_uploaded_file(data_source_pdf)
                
                st.info(f"Files saved as:\n- {os.path.basename(data_source_pdf_path)}")
                
                # Process files
                result = process_pdfs_with_llm(data_source_pdf_path, selected_model, selected_approach, selected_country)

                # Check the type of result
                if isinstance(result, dict) == False:
                    st.error("Processing failed or unexpected response format.")
                    st.error(result)  # Display the string directly
                elif "error" in result:
                    st.error(result)
                else:
                    st.success("Processing complete!")
                    st.write(f"Time taken: {result["time_taken"]:.6f} seconds")

                    if type(result["response"]) == list:
                        for idx, response in enumerate(result["response"]):
                            with st.expander(f"Recommendation #{idx+1}", expanded=True):
                                st.text(response)
                    else:
                        with st.expander("Analysis - Recommendation Response", expanded=True):
                            st.text(result["response"])

                    with st.expander("Cost", expanded=False):
                        st.write(f"Total cost: ${result["total_cost"]:.6f}")

                # Delete the save file
                os.remove(data_source_pdf_path)

if __name__ == "__main__":
    main()