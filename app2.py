from dotenv import load_dotenv
import streamlit as st
import os
from PIL import Image
import google.generativeai as genai
from datetime import datetime # (NEW CODE)
from supabase import create_client, Client


# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- Supabase Setup ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- Session State Initialization (NEW CODE) ---
if "user_data" not in st.session_state:
    st.session_state.user_data = {
        "logged_in": False,
        "name": "",
        "username": "",
        "gender": "",
        "age": 0,
        "height_cm": 0,
        "weight_kg": 0,
        "goal": "",
        "activity_level": 1.2,
        "tdee": 0,
        "user_id": None
    }

if "meal_history" not in st.session_state:
    st.session_state.meal_history = []

if "messages" not in st.session_state:
    st.session_state.messages = []

if "page" not in st.session_state:
    st.session_state.page = "login"

# Function to get Gemini Vision API response using the updated model
def get_gemini_response(image_parts, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([prompt, image_parts[0]])
    return response.text

# Function to process uploaded image
def input_image_setup(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        image_parts = [{
            "mime_type": uploaded_file.type,
            "data": bytes_data
        }]
        return image_parts
    else:
        raise FileNotFoundError("No image uploaded.")

st.set_page_config(page_title="NutriAi", page_icon="🥘", layout="wide")
st.markdown("<h1 style='text-align: center;'>🥘 NutriAi - AI Meal Analyzer</h1>", unsafe_allow_html=True)

# --- LOGIN/SIGNUP PAGE LOGIC ---
def login_page():
    st.title("NutriAi Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username and password:
            # Check user in Supabase
            result = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
            if result.data:
                user = result.data[0]
                st.session_state.user_data.update({
                    "logged_in": True,
                    "username": username,
                    "name": user["name"],
                    "age": user["age"],
                    "gender": user["gender"],
                    "height_cm": user["height_cm"],
                    "weight_kg": user["weight_kg"],
                    "goal": user["goal"],
                    "activity_level": user["activity_level"],
                    "tdee": user["tdee"],
                    "user_id": user["id"]
                })
                st.success("Login successful!")
                st.session_state.page = "main"
                st.rerun()
            else:
                st.error("Invalid username or password.")
        else:
            st.warning("Please enter both username and password.")
    if st.button("Go to Signup"):
        st.session_state.page = "signup"
        st.rerun()

def signup_page():
    st.title("NutriAi Signup")
    name = st.text_input("Name")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    age = st.number_input("Age", min_value=1, max_value=120, value=25)
    gender = st.selectbox("Gender", ["Male", "Female"])
    height = st.number_input("Height (in cm)", min_value=50, max_value=250, value=170)
    weight = st.number_input("Weight (in kg)", min_value=20, max_value=300, value=70)
    goal = st.selectbox("Health Goal", ["Lose Weight", "Maintain Weight", "Gain Muscle"])
    activity = st.selectbox("Activity Level", [
        "Sedentary (little or no exercise)",
        "Lightly Active (light exercise/sports 1-3 days/week)",
        "Moderately Active (moderate exercise/sports 3-5 days/week)",
        "Very Active (hard exercise/sports 6-7 days/week)",
        "Super Active (very hard exercise/sports & physical job)"
    ])
    if st.button("Signup"):
        if name and username and password and age and height and weight:
            activity_map = {
                "Sedentary (little or no exercise)": 1.2,
                "Lightly Active (light exercise/sports 1-3 days/week)": 1.375,
                "Moderately Active (moderate exercise/sports 3-5 days/week)": 1.55,
                "Very Active (hard exercise/sports 6-7 days/week)": 1.725,
                "Super Active (very hard exercise/sports & physical job)": 1.9,
            }
            if gender == "Male":
                bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
            else:
                bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
            tdee = bmr * activity_map[activity]
            # Insert user into Supabase
            result = supabase.table("users").insert({
                "name": name,
                "username": username,
                "password": password,
                "age": age,
                "gender": gender,
                "height_cm": height,
                "weight_kg": weight,
                "goal": goal,
                "activity_level": activity_map[activity],
                "tdee": tdee
            }).execute()
            if result.data:
                st.success("Signup successful! Please login.")
                st.session_state.page = "login"
                st.rerun()
            else:
                st.error("Signup failed. Try a different username.")
        else:
            st.warning("Please fill in all details.")
    if st.button("Go to Login"):
        st.session_state.page = "login"
        st.rerun()

# --- PAGE ROUTING ---
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "signup":
    signup_page()
elif st.session_state.user_data["logged_in"]:
    # --- Main Application Tabs (NEW CODE) ---
    st.sidebar.title(f"Hello, {st.session_state.user_data['name']}!")
    # Display BMR, BMI, and TDEE in the sidebar
    with st.sidebar.expander("Your Health Stats"):
        bmi = st.session_state.user_data["weight_kg"] / ((st.session_state.user_data["height_cm"] / 100)**2)
        st.metric(label="Your BMI", value=f"{bmi:.2f}")
        st.metric(label="Daily Calorie Needs", value=f"{st.session_state.user_data['tdee']:.0f} kcal")

    analyze_tab, plan_tab, chat_tab = st.tabs(["📊 Analyze Meal", "📋 Personalized Meal Plan", "🗣️ Ask NutriAi"])

    # --- MODIFIED: The content of the `analyze_tab` is now personalized ---
    with analyze_tab:
        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader("📤 Upload your delicious meal photo...", type=["jpg", "jpeg", "png"])
            meal_consumed = st.text_input("What meal did you consume? (e.g., Idli, Sambar, Rice, etc.)")
            prep_prompt = st.text_input("Tell us how your meal was prepared (e.g., grilled, fried, steamed) for a more detailed analysis:")
            analyze_clicked = st.button("🍽️ Analyze My Meal")

        with col2:
            if uploaded_file:
                image = Image.open(uploaded_file)
                st.image(image, caption="📸 Uploaded Meal", output_format="JPEG", width=300)
                st.markdown(
                    """
                    <style>
                    img {
                        height: 200px !important;
                        object-fit: contain;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True
                )

        # --- MODIFIED: Base Nutrition prompt is now dynamic and goal-specific (NEW CODE) ---
        user_name = st.session_state.user_data["name"]
        user_goal = st.session_state.user_data["goal"]
        user_tdee = st.session_state.user_data["tdee"]

        base_prompt = f"""
        User Profile:
        Name: {user_name}
        Health Goal: {user_goal}
        Estimated Daily Calorie Needs: {user_tdee:.0f} kcal

        You are an expert nutritionist. Analyze the food items from the image and calculate total calories.
        Provide the analysis in this format:

        FOOD ITEMS AND CALORIES:
        1. Item 1 - XXX calories
        2. Item 2 - XXX calories
        3. Item 3 - XXX calories

        TOTAL CALORIES:
        Your total caloric intake from this meal is XXX calories.

        NUTRITIONAL ANALYSIS:
        - Carbohydrates: XX%
        - Protein: XX%
        - Fat: XX%

        RECOMMENDATION:
        [Your food is healthy/Your food is not healthy] because [reason].
        Suggested improvements: [suggestions].

        GOAL-SPECIFIC FEEDBACK:
        Based on your health goal to "{user_goal}", this meal is [a good choice/not an ideal choice] because [reason]. 
        If you're looking to {user_goal}, you could [suggestion related to their goal].
        """

        input_prompt = base_prompt + ("\nMeal Preparation Details: " + prep_prompt if prep_prompt else "")

        if uploaded_file and analyze_clicked:
            with st.spinner("🔍 Analyzing your meal..."):
                try:
                    image_data = input_image_setup(uploaded_file)
                    response = get_gemini_response(image_data, input_prompt)
                    st.subheader("🧠 Nutritional Analysis:")
                    st.write(response)
                    # Extract calories from response (simple regex)
                    import re
                    calories_match = re.search(r"total caloric intake from this meal is ([\d]+) calories", response, re.IGNORECASE)
                    calories = calories_match.group(1) if calories_match else "N/A"
                    # Save image to Supabase storage
                    image_bytes = uploaded_file.getvalue()
                    image_filename = f"{st.session_state.user_data['username']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                    supabase.storage.from_("meal-images").upload(image_filename, image_bytes)
                    image_url = supabase.storage.from_("meal-images").get_public_url(image_filename)
                    supabase.table("meal_history").insert({
                        "user_id": st.session_state.user_data["user_id"],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "image_url": image_url,
                        "summary": response,
                        "meal_consumed": meal_consumed,
                        "calories": calories
                    }).execute()
                except Exception as e:
                    pass

    # --- Original 'plan_tab' with minor changes to use session state ---
    with plan_tab:
        st.subheader("🍽️ Generate a Personalized Meal Plan")
        diet_preferences = st.text_input(
            f"Hello {st.session_state.user_data['name']}, enter your food preferences (e.g., vegetarian, low-carb, gluten-free, etc.):"
        )
        if st.button("Generate Meal Plan"):
            with st.spinner("Creating your personalized meal plan..."):
                try:
                    meal_plan_prompt = f"Generate a detailed 7-day personalized meal plan for a person with the goal to '{st.session_state.user_data['goal']}'. Their daily calorie need is approximately {st.session_state.user_data['tdee']:.0f} kcal. The meal plan should be based on the following preferences: {diet_preferences}. Include recipes, nutritional information, and a grocery list."
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    meal_plan_response = model.generate_content(meal_plan_prompt)
                    st.subheader("Your 7-Day Personalized Meal Plan:")
                    st.write(meal_plan_response.text)
                    # Store meal plan in Supabase
                    supabase.table("diet_plans").insert({
                        "user_id": st.session_state.user_data["user_id"],
                        "plan": meal_plan_response.text,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }).execute()
                    st.download_button(
                        label="Download Meal Plan 📄",
                        data=meal_plan_response.text,
                        file_name="personalized_meal_plan.txt",
                        mime="text/plain"
                    )
                except Exception as e:
                    pass
        # Button to view last generated meal plan
        if st.button("View Last Generated Meal Plan"):
            result = supabase.table("diet_plans").select("plan", "timestamp").eq("user_id", st.session_state.user_data["user_id"]).order("timestamp", desc=True).limit(1).execute()
            if result.data:
                last_plan = result.data[0]["plan"]
                st.subheader("Last Generated Meal Plan:")
                st.write(last_plan)
            else:
                st.info("No meal plan found. Generate one to see it here.")


    # --- NEW: Ask NutriAi Chat Tab ---
    with chat_tab:
        st.subheader("🗣️ Ask NutriAi")
        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Accept user input
        if prompt := st.chat_input("What would you like to know about nutrition?"):
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            user_info = st.session_state.user_data
            context_prompt = f"""
            User Profile:
            Name: {user_info['name']}
            Age: {user_info['age']}
            Gender: {user_info['gender']}
            Height: {user_info['height_cm']} cm
            Weight: {user_info['weight_kg']} kg
            Goal: {user_info['goal']}
            Daily Calorie Needs: {user_info['tdee']:.0f} kcal

            Based on this user's profile and the following question, act as a personalized nutritionist and provide a helpful response.
            Question: {prompt}
            """

            with st.chat_message("assistant"):
                model = genai.GenerativeModel('gemini-1.5-flash')
                response_obj = model.generate_content(context_prompt)
                st.write(response_obj.text)
            st.session_state.messages.append({"role": "assistant", "content": response_obj.text})
