import streamlit as st

# Set the title of your web app
st.title('🧠 Welcome to the Radiology Assistant')

# Add a line of text
st.write('This is your new web interface. Enter your name below to start.')

# Create a text input box and save what the user types
user_name = st.text_input('Enter your name:', 'Dr. Smith')

# Create a button
if st.button('Say Hello'):
    # This message appears only when the button is clicked
    st.write(f'Hello, **{user_name}**! Ready to work on reports?')
