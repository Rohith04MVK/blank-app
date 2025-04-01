# Import sys at the top if not already there
import sys
import streamlit as st
import google.generativeai as genai
import os
import io
import contextlib
import traceback
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv() # Load environment variables from .env file
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    st.error("🚨 Google API Key not found! Please set the GOOGLE_API_KEY environment variable in your .env file.")
    st.stop()

try:
    genai.configure(api_key=API_KEY)
    # Using 1.5 Flash as it's generally faster and sufficient for this
    model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    st.error(f"🚨 Error configuring Google AI: {e}")
    st.stop()

# --- Safety Settings ---
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# --- Generalized Initial System Prompt (Keep as before) ---
INITIAL_PROMPT = """
You are "CodeCraft Interactive", a friendly, patient, and adaptive AI Python tutor. Your goal is to guide absolute beginners step-by-step through fundamental Python concepts.
Your Teaching Style:
1. **Start Simple & Progress Gradually:** Begin with the very basics (like `print()`). Introduce one small concept or feature at a time. Only move to the next logical concept after the user seems to grasp the current one.
2. **Explain Concepts Clearly:** Use simple language and analogies. Briefly explain the 'why' behind the code. When presenting examples, sometimes include intentional mistakes. Explain these errors, what they mean, and how to fix them.
3. **Give Small Coding Tasks:** Provide specific, small code examples or tasks for the user to try in the editor (e.g., "Try printing your name", "Now try printing the result of 5 + 3"). Use markdown code blocks for code examples.
4. **Instruct Clearly:** Explicitly tell the user what code to type and instruct them to press the "Run Code" button. Include tasks where the code has an error, and then guide them through debugging that error.
5. **Evaluate Code Submissions:** When the user runs code, review their code and the output or error message. Assess if they successfully completed the task or if they encountered an error.

6. **Provide Constructive Feedback:**
   - **On Success:** Praise gently ("Nice!", "Exactly!", "Great job!"). Then, introduce the next small step or concept.
   - **On Error:** Treat errors as valuable learning opportunities.
     - Calmly acknowledge the error ("Okay, looks like we got an error. That's normal! Let's figure it out.").
     - Help the user read the error message. Explain what the error type (e.g., `SyntaxError`, `NameError`, `TypeError`) means in simple terms.
     - Point out the part of the code where the error occurred.
     - Explain the underlying Python rule or concept that caused the error (e.g., "Python needs quotes around text", "You can't add a number and text directly").
     - Gently suggest how to fix the code and provide a corrected code snippet if needed.
7. **Handle User Questions:** When a user asks a question, answer directly and clearly. Relate the answer back to the learning path if possible, or ask if they'd like to try a related coding task.
8. **Maintain Context:** Remember what you've already taught or discussed in the current session, including any errors encountered and resolved.
9. **Be Encouraging:** Use a positive and patient tone. Include emojis occasionally 😊👍✨. Keep responses focused and supportive.
Overall, use intentional errors as teaching moments to help learners understand both what went wrong and how to fix it. This approach reinforces debugging skills and builds confidence.
"""

# --- Streamlit App Layout ---
st.set_page_config(layout="wide")
st.title("🐍 CodeCraft Interactive Tutor")
st.caption("Follow the AI's guidance. Ask questions below the chat.")

# --- Initialize Session State ---
if 'chat' not in st.session_state:
    try:
        # Initialize the actual chat history with the system prompt
        st.session_state.chat = model.start_chat(history=[
             {'role':'user', 'parts': [INITIAL_PROMPT]},
             {'role':'model', 'parts': ["Okay, I'm ready to start teaching Python basics interactively! I'll begin with the `print()` function."]}
        ])

        # Generate the first user-visible message from the AI
        first_user_instruction = "Give the user the very first instruction: Explain the `print()` function briefly and ask them to print the message 'Hello, Learner!' using `print(\"Hello, Learner!\")`."
        response = st.session_state.chat.send_message(first_user_instruction, stream=False, safety_settings=safety_settings)

        # Initialize the display messages list (FULL history is stored here)
        st.session_state.messages = [{'role':'assistant', 'content': response.text}]
        st.session_state.current_code = 'print("Hello, Learner!")'

    except Exception as e:
         st.error(f"🚨 Failed to start chat. Error: {e}\n{traceback.format_exc()}")
         st.stop()

# Ensure other states exist if chat does
if 'messages' not in st.session_state:
     st.session_state.messages = []
if 'current_code' not in st.session_state:
    st.session_state.current_code = ''


# --- Main App Columns ---
col1, col2 = st.columns(2)

with col1:
    st.header("💬 Tutor Guidance")

    # --- MODIFIED Chat Display Logic ---
    # Find the most recent assistant message and the most recent user message
    last_assistant_msg = None
    last_user_msg = None

    # Iterate backwards through the full message history
    for msg in reversed(st.session_state.messages):
        if msg['role'] == 'assistant' and last_assistant_msg is None:
            last_assistant_msg = msg
        elif msg['role'] == 'user' and last_user_msg is None:
            last_user_msg = msg
        # Stop if we've found both most recent ones
        if last_assistant_msg and last_user_msg:
            break

    # Display the messages in logical order (Assistant first, then User action/result)
    # Or just the assistant if it's the only one or the most recent.
    if last_assistant_msg:
        with st.chat_message("assistant"):
            st.markdown(last_assistant_msg['content'])
    if last_user_msg and (not last_assistant_msg or st.session_state.messages.index(last_user_msg) > st.session_state.messages.index(last_assistant_msg)):
         # Display user message only if it exists and is more recent than the displayed assistant message (or if no assistant message found)
        with st.chat_message("user"):
             st.markdown(last_user_msg['content'])
    # --- END MODIFIED Chat Display Logic ---


    # Chat Input Box - stays the same
    if prompt := st.chat_input("Ask a question or type 'next'..."):
        # Add user text message to FULL history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Send user text message to AI and get response
        try:
            response = st.session_state.chat.send_message(prompt, stream=False, safety_settings=safety_settings)
            # Add AI response to FULL history
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            # Rerun to update display (which will now filter)
            st.rerun()
        except Exception as e:
             st.error(f"🚨 Error communicating with AI: {e}")


with col2:
    st.header("📝 Code Editor")

    # Code input area - Use key and session state
    st.session_state.current_code = st.text_area(
        "Type your Python code here:",
        value=st.session_state.current_code, # Use current_code from state
        height=300,
        key="code_input_area"
    )

    # --- Button and Execution Logic ---
    if st.button("Run Code ▶️", key="run_button"):
        user_code = st.session_state.current_code
        st.info(f"Running code...") # Feedback that button was pressed

        # Prepare user message content (code + result placeholder)
        # We will add the result *after* execution
        user_submission_content = f"```python\n{user_code}\n```"
        # Add the user submission (without result yet) to the *full* message history
        st.session_state.messages.append({"role": "user", "content": user_submission_content})


        # Execute code and capture output/errors
        output_capture = io.StringIO()
        execution_result = ""
        error_occurred = False
        error_details = "" # For AI context
        result_display_content = "" # For display below editor *and* appending to message

        try:
            with contextlib.redirect_stdout(output_capture):
                 exec(user_code, {}) # UNSAFE
            execution_result = output_capture.getvalue().strip()
            result_display_content = execution_result or "✅ Code ran successfully (No output)"

        except Exception: # Catch any exception
            error_occurred = True
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_short = f"{exc_type.__name__}: {exc_value}"
            result_display_content = f"💥 {error_short}"
            error_details = traceback.format_exc() # Full traceback for AI

        # --- Display Result Temporarily Under Editor ---
        st.subheader("Result:")
        if error_occurred:
            st.error(result_display_content)
        else:
            if execution_result:
                 st.code(result_display_content, language="text")
            else:
                 st.code(result_display_content, language="text") # Display success message
        # --- This temporary display WILL disappear on the next rerun ---

        # --- Update the user message in history to include the result ---
        st.session_state.messages[-1]["content"] += f"\n**Result:**\n```text\n{result_display_content}\n```"


        # --- Send code execution context to Gemini ---
        if st.session_state.chat:
            try:
                # Prepare prompt for AI evaluation after code run
                ai_context = error_details if error_occurred else execution_result
                ai_prompt = (
                    f"The user ran the code shown in their last message. The result/output was:\n"
                    f"```text\n{result_display_content}```\n\n" # Send the display result string
                    f"(Full error trace if any: {error_details})\n\n"
                    f"Please evaluate this based on the conversation context/last task. "
                    f"Provide feedback according to the teaching style: praise success and suggest the next logical small step, OR if there was an error, explain the error message/concept and guide towards the fix."
                 )

                response = st.session_state.chat.send_message(ai_prompt, stream=False, safety_settings=safety_settings)

                # Add AI response to FULL history
                st.session_state.messages.append({"role": "assistant", "content": response.text})

                # Rerun the app. This will redraw the chat area showing only the latest msgs
                # and the temporary result under the editor will not be redrawn.
                st.rerun()

            except Exception as e:
                st.error(f"🚨 Error communicating with AI: {e}\n{traceback.format_exc()}")
        else:
            st.error("Chat session not initialized.")

# Add a footer or separator
st.divider()
st.caption("Ask questions below the chat or follow the AI's coding tasks!")