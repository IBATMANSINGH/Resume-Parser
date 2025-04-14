# --- Core Libraries ---
import streamlit as st  # For the web app interface
import spacy           # For NLP tasks
import pandas as pd    # For data handling (DataFrames)
import PyPDF2          # For reading PDF files
import docx            # For reading DOCX files
import re              # For regular expressions (finding patterns like email/phone)
import os              # For interacting with the operating system (like getting file extensions)
import io              # For handling file data in memory
from collections import Counter # Useful for counting things (though not heavily used in this simple version)

# --- Configuration ---

# Tell spaCy which language model to use. Make sure you downloaded this!
SPACY_MODEL = "en_core_web_sm"

# DEFINE THE SKILLS YOU WANT TO SEARCH FOR.
# THIS IS THE MOST IMPORTANT LIST TO CUSTOMIZE!
TARGET_SKILLS = [
    'python', 'java', 'c++', 'javascript', 'sql', 'nosql', 'mongodb', 'postgresql',
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'git', 'jira', 'agile', 'scrum',
    'machine learning', 'deep learning', 'nlp', 'natural language processing',
    'data analysis', 'data science', 'pandas', 'numpy', 'scikit-learn', 'tensorflow',
    'pytorch', 'react', 'angular', 'vue', 'node.js', 'flask', 'django',
    'project management', 'communication', 'teamwork', 'problem solving'
    # Add/remove skills relevant to the jobs you typically recruit for
]

# Explanation:
# - Imports bring in the tools (libraries) we need.
# - SPACY_MODEL tells the code which pre-trained language model to use.
# - TARGET_SKILLS is a Python list containing the keywords the program will search for in resumes and job descriptions. You *must* edit this list to be relevant to your needs.





# --- Load spaCy Model ---
# Use st.cache_resource to load the model only once, speeding up the app after the first run.
@st.cache_resource # Decorator to cache the loaded model
def load_spacy_model(model_name):
    """Loads the spaCy model and handles potential errors."""
    try:
        # Attempt to load the specified spaCy model
        return spacy.load(model_name)
    except OSError:
        # If the model isn't found, show an error message in the app and stop.
        st.error(f"spaCy model '{model_name}' not found. Please download it: python -m spacy download {model_name}")
        st.stop() # Stop the Streamlit app execution

# Load the model when the script starts (or retrieve from cache)
nlp = load_spacy_model(SPACY_MODEL)

# Explanation:
# - We define a function `load_spacy_model` to handle loading.
# - `@st.cache_resource`: This is a Streamlit feature. It means the first time `load_spacy_model` is called, it will execute fully (load the model from disk, which can be slow). On subsequent runs or page refreshes, Streamlit will reuse the already loaded model from memory (cache), making the app much faster.
# - `try...except OSError`: This safely handles the situation where the user forgot to download the model. It shows an error instead of crashing.
# - `nlp = load_spacy_model(SPACY_MODEL)`: This line actually calls the function and stores the loaded spaCy model in the `nlp` variable, making it ready to use for text analysis.





# --- Text Extraction Functions ---

def extract_text_from_pdf(file_content):
    """Extracts text from PDF file content (bytes)."""
    text = ""
    try:
        # Create a PDF reader object from the file content (which is in memory)
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        # Loop through each page in the PDF
        for page in pdf_reader.pages:
            # Extract text from the current page
            page_text = page.extract_text()
            # Add the extracted text to our overall text string
            if page_text: # Check if text was actually extracted
                 text += page_text + "\n" # Add a newline for separation
    except Exception as e:
        # If any error occurs during PDF reading, show a warning in the app
        st.warning(f"Could not read PDF: {e}")
    return text # Return the extracted text (or empty string if failed)

def extract_text_from_docx(file_content):
    """Extracts text from DOCX file content (bytes)."""
    text = ""
    try:
        # Create a Document object from the file content
        doc = docx.Document(io.BytesIO(file_content))
        # Loop through each paragraph in the Word document
        for para in doc.paragraphs:
            # Add the text of the paragraph to our overall text string
            text += para.text + "\n" # Add a newline for separation
    except Exception as e:
        # If any error occurs during DOCX reading, show a warning
        st.warning(f"Could not read DOCX: {e}")
    return text # Return the extracted text

def extract_text(uploaded_file):
    """Determines file type and calls the appropriate extraction function."""
    # Get the raw bytes content of the uploaded file
    file_content = uploaded_file.getvalue()
    # Get the file extension (e.g., '.pdf', '.docx') and convert to lowercase
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()

    # Check the extension and call the correct function
    if file_extension == ".pdf":
        return extract_text_from_pdf(file_content)
    elif file_extension == ".docx":
        return extract_text_from_docx(file_content)
    else:
        # If the file type isn't supported, show a warning and return nothing
        st.warning(f"Unsupported file type: {uploaded_file.name}")
        return ""

# Explanation:
# - We need functions to handle different resume file formats (PDF, DOCX).
# - `io.BytesIO(file_content)`: Streamlit's `uploaded_file.getvalue()` gives us the file content as raw bytes. Libraries like `PyPDF2` and `docx` need file-like objects, so `io.BytesIO` wraps these bytes to make them readable like a file in memory.
# - `extract_text_from_pdf`: Uses the `PyPDF2` library to open the PDF bytes, loop through pages, and extract text.
# - `extract_text_from_docx`: Uses the `python-docx` library to open the DOCX bytes, loop through paragraphs, and extract text.
# - `extract_text`: This acts as a control function. It checks the uploaded file's extension (`.pdf` or `.docx`) and calls the corresponding specific extraction function. It handles unsupported file types gracefully.





# --- Information Extraction Functions ---

def extract_contact_info(text):
    """Extracts email and phone number using simple regex."""
    # Regex for finding email addresses
    email = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    # Basic regex for North American phone numbers (can be improved for international)
    phone = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    # Return the first found email/phone, or None if not found
    return email[0] if email else None, phone[0] if phone else None

def extract_name(text, nlp_model):
    """Extracts the most likely candidate name using spaCy NER."""
    # Process the text with the loaded spaCy model
    doc = nlp_model(text)
    # Find entities labeled as "PERSON" by the spaCy model
    person_names = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]

    # VERY basic logic: Assume the first multi-word name is the candidate's.
    # This often fails on resumes with multiple names (references, etc.)
    for name in person_names:
        if len(name.split()) > 1: # Check if the name has more than one part
            return name
    # If no multi-word name found, return the first person name found (if any)
    return person_names[0] if person_names else None

def extract_skills(text, skills_list):
    """Extracts skills from the text based on the predefined TARGET_SKILLS list."""
    found_skills = set() # Use a set to automatically avoid duplicate skill entries
    text_lower = text.lower() # Convert text to lowercase for case-insensitive matching
    # Check for each skill in our target list
    for skill in skills_list:
        skill_lower = skill.lower() # Convert skill to lowercase
        # Create a regex pattern to find the skill as a whole word
        # `\b` matches word boundaries (spaces, punctuation) to avoid partial matches (e.g., 'java' in 'javascript')
        pattern = r'\b' + re.escape(skill_lower) + r'\b'
        # Search for the pattern in the lowercased text
        if re.search(pattern, text_lower):
            # If found, add the original skill (not lowercased) to the set
            found_skills.add(skill)
    return list(found_skills) # Return the found skills as a list

# Explanation:
# - Now that we have the raw text, we extract specific details.
# - `extract_contact_info`: Uses regular expressions (`re.findall`) to search for patterns that look like email addresses and phone numbers. These patterns might need adjustment for different formats.
# - `extract_name`: Uses the spaCy `nlp` model. `nlp(text)` processes the text, and `doc.ents` contains the "entities" (like names, organizations, dates) spaCy found. We filter for `ent.label_ == "PERSON"`. The logic to pick the *correct* name is very basic here and is a common challenge.
# - `extract_skills`: This function iterates through our predefined `TARGET_SKILLS` list. For each skill, it searches the resume text (converted to lowercase) to see if that skill keyword exists as a whole word (`\b` ensures this). Found skills are collected.





# --- Ranking Function ---

def calculate_match_score(resume_skills, job_desc_keywords):
    """Calculates a simple match score based on skill overlap."""
    # Find the common skills between the resume and the job description
    common_skills = set(resume_skills).intersection(set(job_desc_keywords))
    # The score is simply the count of common skills
    score = len(common_skills)
    return score

# Explanation:
# - This function determines how well a resume matches the job description.
# - The current logic is *very simple*: it just counts how many skills from the `TARGET_SKILLS` list were found in *both* the resume and the job description.
# - `set(resume_skills).intersection(set(job_desc_keywords))` finds the common elements between the two lists of skills.
# - A real-world application would need a more sophisticated scoring system (e.g., weighting important skills higher, considering years of experience, education).





# --- Main Streamlit App ---

# Configure the page layout (optional, 'wide' uses more screen space)
st.set_page_config(layout="wide")

# Set the title of the web application page
st.title("📄 Resume Parser & Ranker")
# Add some introductory text using Markdown
st.markdown("Upload multiple resumes (PDF or DOCX) and paste a job description to rank candidates based on skill match.")
st.markdown("---") # Adds a horizontal line separator

# --- Sidebar for User Inputs ---
# 'with st.sidebar:' puts the following elements into a collapsible sidebar
with st.sidebar:
    st.header("Inputs") # Sidebar header

    # File uploader widget
    uploaded_files = st.file_uploader(
        "Upload Resumes",
        type=["pdf", "docx"], # Allow only PDF and DOCX files
        accept_multiple_files=True, # Allow uploading more than one file
        help="Upload one or more resumes in PDF or DOCX format." # Tooltip help text
    )

    # Display some of the target skills being searched for
    st.subheader("Target Skills")
    st.info(f"Currently looking for these skills:\n - {', '.join(TARGET_SKILLS[:15])}...") # Show first 15 skills

    # Text area for pasting the job description
    st.header("Job Description")
    job_description = st.text_area("Paste Job Description Here", height=300) # Creates a multi-line text input box

    # Button to trigger the processing
    process_button = st.button("Process Resumes", type="primary") # Make it a prominent button

# --- Main Area for Displaying Results ---

# Check if the button was pressed AND if files were uploaded AND if a job description was entered
if process_button and uploaded_files and job_description:
    st.header("Processing Results") # Header for the results section
    # Show a loading indicator while processing
    with st.spinner("Parsing resumes and ranking candidates... Please wait."):

        # 1. Extract Keywords from Job Description
        job_desc_lower = job_description.lower() # Convert JD to lowercase
        # Use the same skill extraction function on the JD text
        job_keywords = extract_skills(job_desc_lower, TARGET_SKILLS)
        st.subheader("Skills Found in Job Description:")
        if job_keywords:
             # Display the skills found in the JD
             st.write(", ".join(sorted(job_keywords)))
        else:
             st.warning("No target skills found in the job description. Ranking might be ineffective.")

        # 2. Process Each Uploaded Resume
        results = [] # List to store the data extracted from each resume
        total_files = len(uploaded_files)
        progress_bar = st.progress(0) # Initialize progress bar

        # Loop through each uploaded file
        for i, file in enumerate(uploaded_files):
            st.write(f"Processing: {file.name}...") # Show which file is being processed
            # Extract raw text from the file using our function
            resume_text = extract_text(file)

            # Handle cases where text extraction failed
            if not resume_text:
                 st.write(f"  -> Could not extract text from {file.name}.")
                 # Add a placeholder entry for failed files
                 results.append({
                    'Filename': file.name, 'Name': 'Extraction Failed', 'Email': 'N/A',
                    'Phone': 'N/A', 'Skills Found': [], 'Score': 0, 'Raw Text': ''
                 })
                 # Update progress bar and skip to the next file
                 progress_bar.progress((i + 1) / total_files)
                 continue

            # Extract specific information using our functions
            name = extract_name(resume_text, nlp)
            email, phone = extract_contact_info(resume_text)
            skills_found = extract_skills(resume_text, TARGET_SKILLS)

            # Calculate the match score against the job keywords
            score = calculate_match_score(skills_found, job_keywords)

            # Store the extracted data for this resume in a dictionary
            results.append({
                'Filename': file.name,
                'Name': name if name else 'Not Found', # Use 'Not Found' if extraction failed
                'Email': email if email else 'Not Found',
                'Phone': phone if phone else 'Not Found',
                'Skills Found': sorted(skills_found), # Sort skills alphabetically
                'Score': score,
                'Raw Text': resume_text # Keep the raw text for potential review
            })
            # Update the progress bar
            progress_bar.progress((i + 1) / total_files)

        # 3. Create DataFrame and Rank
        # Convert the list of dictionaries into a Pandas DataFrame
        results_df = pd.DataFrame(results)
        # Sort the DataFrame by the 'Score' column in descending order (highest score first)
        ranked_df = results_df.sort_values(by="Score", ascending=False).reset_index(drop=True)

        # 4. Display Ranked Results
        st.success("Processing Complete!") # Show a success message
        st.subheader("Ranked Candidates")

        # Define which columns to show in the main results table
        display_columns = ['Rank', 'Filename', 'Name', 'Score', 'Skills Found', 'Email', 'Phone']
        # Add a 'Rank' column starting from 1
        ranked_df.index = ranked_df.index + 1
        ranked_df['Rank'] = ranked_df.index

        # Display the ranked DataFrame as an interactive table
        st.dataframe(ranked_df[display_columns], use_container_width=True)

        # --- Optional: Allow viewing details of a specific candidate ---
        st.subheader("View Resume Details")
        # Create a dropdown menu with the ranks (1, 2, 3...)
        selected_rank = st.selectbox("Select Rank to View Raw Text & Details:", ranked_df.index)
        if selected_rank:
            # Get the data for the selected candidate from the DataFrame using its rank (index)
            selected_candidate = ranked_df.loc[selected_rank]
            # Display the details of the selected candidate
            st.write(f"**Details for Rank {selected_rank} ({selected_candidate['Filename']})**")
            # ... display other fields ...
            st.write(f"**Matched Skills:** {', '.join(selected_candidate['Skills Found'])}")
            st.write(f"**Match Score:** {selected_candidate['Score']}")
            # Use an expander to optionally show the full raw text
            with st.expander("Show Raw Extracted Text"):
                st.text_area("", selected_candidate['Raw Text'], height=400, key=f"raw_text_{selected_rank}")

# Handle cases where the button is pressed but inputs are missing
elif process_button:
    st.warning("Please upload resumes and paste a job description before processing.")

# Initial state of the app before the button is pressed
else:
    st.info("Upload resumes and provide a job description in the sidebar to begin.")


# Explanation:
# - `st.set_page_config`, `st.title`, `st.markdown`: Basic Streamlit commands to set up the page title and text.
# - `with st.sidebar:`: Creates the sidebar section.
# - `st.file_uploader`, `st.text_area`, `st.button`: These are Streamlit *widgets* that create the interactive elements (upload box, text box, button) for the user.
# - `if process_button and uploaded_files and job_description:`: This is the main logic block. It only runs *after* the user has provided all inputs and clicked the button.
# - `st.spinner`: Shows a "waiting" message while the potentially long processing happens.
# - **Job Description Processing:** It first analyzes the job description to find the target skills within it.
# - **Resume Processing Loop:** It then goes through each uploaded resume file:
#     - Extracts text (`extract_text`).
#     - Extracts name, contact, skills (`extract_name`, `extract_contact_info`, `extract_skills`).
#     - Calculates the score (`calculate_match_score`).
#     - Stores all this information in the `results` list.
#     - Updates a `st.progress_bar`.
# - **DataFrame and Ranking:** Converts the `results` list into a Pandas DataFrame (`pd.DataFrame`) which is like a spreadsheet table. Then, it sorts this table (`sort_values`) based on the 'Score'.
# - **Displaying Results:** Uses `st.dataframe` to show the ranked table. It also adds an optional `st.selectbox` to let the user choose a candidate and see their extracted details and the raw resume text within an `st.expander`.
# - The `elif` and `else` blocks handle the display when the user hasn't provided all inputs or hasn't clicked the button yet.