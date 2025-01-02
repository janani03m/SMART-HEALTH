from django.shortcuts import render

from django.shortcuts import render,redirect
import mysql.connector as sql
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
import re
import requests
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.conf import settings
from .models import Doctor, Patient, Appointment, WellnessTransaction
import io
import base64
import matplotlib.pyplot as plt
from django.http import JsonResponse
import matplotlib
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.contrib.auth import get_user_model

def home(request):
    return render(request, 'myapp/home.html',{'is_authenticated': request.user.is_authenticated})

User = get_user_model()

def check_password_strength(password):
    # Implement your password strength checking logic here
    # Example: Ensure password is at least 8 characters long, contains upper/lowercase letters, etc.
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number."
    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(char in '!@#$%^&*()_+' for char in password):
        return False, "Password must contain at least one special character."
    return True, ""
def registration(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        cpassword = request.POST['cpassword']

        # Check if passwords match
        if password != cpassword:
            messages.error(request, "Passwords do not match.")
        else:
            # Check for existing email or username
            if User.objects.filter(email=email).exists():
                messages.error(request, "An account with this email already exists.")
            elif User.objects.filter(username=username).exists():
                messages.error(request, "Username already taken.")
            else:
                # Email validation
                try:
                    validator = EmailValidator()
                    validator(email)  # Will raise ValidationError if invalid
                except ValidationError:
                    messages.error(request, "Invalid email format. Please enter a valid email address.")
                else:
                    # Check password strength
                    is_valid, error_message = check_password_strength(password)
                    if not is_valid:
                        messages.error(request, error_message)
                    else:
                        # Create user if email is valid and password is strong
                        User.objects.create_user(username=username, email=email, password=password)
                        messages.success(request, "Registration successful! You can now log in.")
                        return redirect('login')  # Redirect to login page

    return render(request, 'myapp/registration.html')


@csrf_protect
def login(request):
    if request.method == "POST":
        # Get username and password from the form
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        # Authenticate the user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Log the user in
            auth_login(request, user)
            messages.success(request, "Login successful!")
            # Redirect to the success page
            return redirect('home')  # Make sure to create a success URL
        else:
            error_message = "Invalid username or password."
            return render(request, 'login.html', {'error_message': error_message})

    return render(request,'myapp/login.html')

# Logout View
def logout(request):
   
    auth_logout(request)  # Use Django's built-in logout function
    messages.success(request, "Logged out successfully.")
    return redirect('home')





 
def dashboard(request):
    # Get counts for doctors, patients, and appointments
    total_doctors = Doctor.objects.count()
    total_patients = Patient.objects.count()
    total_appointments = Appointment.objects.count()  # Count of appointments
 
    # Fetch recent doctors, patients, and appointments with relevant fields
    recent_doctors = Doctor.objects.all().order_by('-id')[:3]  # Limit to the latest 3 doctors
    recent_patients = Patient.objects.all().order_by('-id')[:3]  # Limit to the latest 3 patients
    # recent_appointments = Appointment.objects.all().order_by('-appointment_date')[:3]  # Latest 3 appointments
    recent_appointments = Appointment.objects.all().order_by('-appointment_date')[:3]  # Latest 3 appointments
 
    # Context to pass to the template
    context = {
        'total_doctors': total_doctors,
        'total_patients': total_patients,
        'total_appointments': total_appointments,
        'recent_doctors': recent_doctors,
        'recent_patients': recent_patients,
        'recent_appointments': recent_appointments,
    }
 
    return render(request,'myapp/dashboard.html', context)

from django.db.models import Q
 
def wellnesstracking(request):
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        transactions = WellnessTransaction.objects.filter(
            Q(category__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    else:
        transactions = WellnessTransaction.objects.all()
 
    # Pass transactions to the template
    return render(request,'myapp/wellnesstracking.html', {
        'transactions': transactions,
        'search_query': search_query
    })



import json
from django.http import JsonResponse

import google.generativeai as ai

# Function to load the API key from config.json
def load_api_key():
    try:
        with open('config.json') as f:
            config = json.load(f)
            return config.get('API_KEY')
    except FileNotFoundError:
        print("Error: config.json file not found.")
        return None

# Function to generate health advice based on user input
def health_suggestions(request):
    api_key = load_api_key()
    
    if not api_key:
        return JsonResponse({"error": "API key not found."})
    
    ai.configure(api_key=api_key)
    model = ai.GenerativeModel("gemini-pro")
    chat = model.start_chat()
    
    if request.method == "POST":
        user_input = request.POST.get("user_input", "")
        
        # AI prompt for concise suggestions
        prompt = f"Provide 5-10 short points for home remedies or health advice for: {user_input}"

        try:
            response = chat.send_message(prompt)
            suggestions = response.text.strip()

            # Split the response into sentences or lines
            points = suggestions.split("\n")
            points = [point.strip() for point in points if point.strip() != ""]  # Clean up whitespace
            short_points = points[:10]  # Limit to 5-10 points

            # Format the suggestions into bullet points
            bullet_points = [f"{point}" for point in short_points]

            return JsonResponse({"suggestions": bullet_points})

        except Exception as e:
            return JsonResponse({"error": str(e)})
    
    return render(request, "suggestions.html")

 

import io
import base64
import matplotlib.pyplot as plt
from django.http import JsonResponse
import matplotlib
matplotlib.use('Agg')
from django.shortcuts import render
def generate_comparison_graph(data, metric_name, normal_range):
    categories = ["Given", "Normal Range"]
    values = [data, normal_range]
    
    # Create figure for the chart
    plt.figure(figsize=(6, 4))
    plt.bar(categories, values, color=["orange", "green"])
    plt.title(f"{metric_name} Comparison")
    plt.ylabel(metric_name)
    
    # Save plot to a BytesIO object
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)
    
    # Encode to base64
    graph_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()
    
    return graph_base64

# Function to get recommendation from Google Gemini AI
def get_gemini_ai_recommendation(health_data):
    api_key = load_api_key()
    
    if not api_key:
        return {"error": "API key not found."}
    
    ai.configure(api_key=api_key)
    model = ai.GenerativeModel("gemini-pro")
    chat = model.start_chat()

    # AI prompt for generating health recommendations
    prompt = (f"Based on the following health data, give recommendations if they are not in good health range \n"
              f"Heart Rate: {health_data.get('heart_rate')}\n"
              f"Sleep Hours: {health_data.get('sleep_hours')}\n"
              f"Steps: {health_data.get('steps')}\n"
              f"Calories Burnt: {health_data.get('calories_burnt')}")
    
    try:
        # Send the prompt to the AI model for health recommendations
        response = chat.send_message(prompt)
        recommendations = response.text.strip()

        # Split the response into bullet points
        points = recommendations.split("\n")
        points = [point.strip() for point in points if point.strip() != ""]
        short_points = points[:10]  # Limit to 5-10 points
        bullet_points = [f"• {point}" for point in short_points]
        
        return bullet_points

    except Exception as e:
        return {"error": str(e)}

def healthinsights(request):
    if request.method == "POST":
        # Collect health data from POST request
        heart_rate = float(request.POST.get("heart_rate", 70))
        sleep_hours = float(request.POST.get("sleep_hours", 8))
        steps = int(request.POST.get("steps", 10000))
        calories_burnt = float(request.POST.get("calories_burnt", 250))

        # Normal ranges
        heart_rate_normal = 77  # Normal range for heart rate (bpm)
        sleep_normal = 8  # Normal range for sleep hours
        steps_normal = 6000  # Normal range for steps
        calories_burnt_normal = 3000  # Normal range for calories burnt

        # Generate graphs for each metric
        heart_rate_graph = generate_comparison_graph(heart_rate, "Heart Rate (bpm)", heart_rate_normal)
        sleep_graph = generate_comparison_graph(sleep_hours, "Sleep Hours (hours)", sleep_normal)
        steps_graph = generate_comparison_graph(steps, "Steps", steps_normal)
        calories_graph = generate_comparison_graph(calories_burnt, "Calories Burnt (kcal)", calories_burnt_normal)

        # Prepare health data for AI recommendation
        health_data = {
            "heart_rate": heart_rate,
            "sleep_hours": sleep_hours,
            "steps": steps,
            "calories_burnt": calories_burnt
        }

        # Get AI-generated recommendations
        ai_recommendation = get_gemini_ai_recommendation(health_data)

        # Return both graphs and AI response in the JSON response
        return JsonResponse({
            "heart_rate_graph": heart_rate_graph,
            "sleep_graph": sleep_graph,
            "steps_graph": steps_graph,
            "calories_graph": calories_graph,
            "recommendations": ai_recommendation
        })

    return render(request, "myapp/healthinsights.html")





