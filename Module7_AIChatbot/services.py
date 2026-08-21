import os
import re
import json
import random
import requests
from database import db
from models.user import User
from Module2_EmployeeHealthData.models import EmployeeHealth
from Module7_AIChatbot.models import CheckupAppointment, ChatMessage

WELLNESS_NLP_DICTIONARY = {
    "greeting": [
        "Hello! I am your AI Wellness Coach. How can I assist you with your health goals, workouts, or appointments today?",
        "Hi there! Ready to focus on your health today? Ask me about your BMI, scheduling checkups, or healthy habits!"
    ],
    "motivation": [
        "Remember: 'The only bad workout is the one that didn't happen.' Stay active and keep going!",
        "Health is a journey, not a destination. Small daily changes add up to massive results over time!",
        "Hydrate, sleep well, and take a deep breath. You're doing great!"
    ],
    "bmi_info": "Body Mass Index (BMI) categories: Underweight (< 18.5), Normal (18.5 - 24.9), Overweight (25 - 29.9), and Obese (>= 30). Logging regular exercise and fiber-rich diets helps maintain normal BMI ratios.",
    "checkup": "I can help you schedule a virtual checkup appointment. Just type 'schedule checkup' or click the action chip above!",
    "water": "Drinking 2.5 - 3.0 Litres of water daily increases mental clarity, improves skin hydration, and balances cardiovascular pressures.",
    "default": "I'm here to help you schedule checkups, track goals, and review your vitals! Try asking 'Is my BMI healthy?' or 'Schedule a checkup'."
}

MULTILINGUAL_INTENT_REPLIES = {
    "hi-IN": {
        "booking": "📅 मैंने आपके लिए एक वर्चुअल स्वास्थ्य जांच नियुक्ति निर्धारित की है!\n\n**डॉक्टर**: {doctor}\n**समय**: {date_str}\n\nयह आपके अपॉइंटमेंट शेड्यूल पैनल में दर्ज किया गया है।",
        "vitals": "🩺 **आपकी सक्रिय स्वास्थ्य प्रोफ़ाइल ओवरव्यू**:\n\n*   **बीएमआई (BMI)**: {bmi} ({bmi_category})\n*   **हृदय गति (Heart Rate)**: {heart_rate} bpm\n*   **तनाव स्तर (Stress)**: {stress_level}\n*   **स्वास्थ्य जोखिम (Risk)**: {health_risk_score}%\n*   **वेलनेस स्कोर**: {wellness_score}/100",
        "diet": "🥗 **अनुकूलित आहार योजना**:\n*   **नाश्ता**: बादाम और जामुन के साथ दलिया।\n*   **दोपहर का भोजन**: ग्रिल्ड पनीर/चिकन और क्विनोआ सलाद।\n*   **स्नैक**: अखरोट और ग्रीक योगर्ट।\n*   **रात का खाना**: दाल का सूप और हरी सब्जियां।",
        "workout": "🏃 **अनुशंसित कसरत योजना**:\n*   **कार्डियो**: सप्ताह में 3-4 दिन 30 मिनट तेज चाल या साइकिल चलाना।\n*   **स्ट्रेंथ**: सप्ताह में 2 दिन बॉडीवेट स्क्वैट्स और प्लैंक।\n*   **लचीलापन**: 10 मिनट स्ट्रेचिंग।",
        "stress": "🧘 **कार्यस्थल तनाव राहत उपाय**:\n*   स्क्रीन ब्रेक के दौरान 3 मिनट तक **4-7-8 बॉक्स ब्रीदिंग** का अभ्यास करें।\n*   5 मिनट की टहलने की ब्रेक लें और गर्दन/कंधों को घुमाएं।",
        "sleep": "🌙 **उत्कृष्ट नींद की रणनीति**:\n*   शारीरिक रिकवरी के लिए प्रति रात 7.5 - 8 घंटे की नींद लें।\n*   सोने से 45 मिनट पहले स्क्रीन बंद कर दें।",
        "greeting": "नमस्ते! मैं आपका AI वेलनेस कोच हूं। आज मैं आपकी स्वास्थ्य लक्ष्यों में कैसे सहायता कर सकता हूं?",
        "motivation": "याद रखें: 'एकमात्र खराब कसरत वह है जो नहीं हुई।' सक्रिय रहें!",
        "water": "प्रतिदिन 2.5 - 3.0 लीटर पानी पीने से मानसिक स्पष्टता बढ़ती है और त्वचा हाइड्रेट रहती है।",
        "no_profile": "आपके पास अभी तक कोई स्वास्थ्य प्रोफ़ाइल दर्ज नहीं है। कृपया पहले अपनी स्वास्थ्य जानकारी दर्ज करें!"
    },
    "te-IN": {
        "booking": "📅 నేను మీ కోసం వర్చువల్ ఆరోగ్య పరీక్ష అపాయింట్‌మెంట్‌ను షెడ్యూల్ చేసాను!\n\n**వైద్యుడు**: {doctor}\n**సమయం**: {date_str}\n\nఇది మీ అపాయింట్‌మెంట్ షెడ్యూల్ ప్యానెల్‌లో నమోదు చేయబడింది.",
        "vitals": "🩺 **మీ క్రియాశీల ఆరోగ్య ప్రొఫైల్ వివరాలు**:\n\n*   **BMI**: {bmi} ({bmi_category})\n*   **గుండె వేగం**: {heart_rate} bpm\n*   **ఒత్తిడి స్థాయి**: {stress_level}\n*   **ఆరోగ్య ప్రమాదం**: {health_risk_score}%\n*   **వెల్నెస్ స్కోర్**: {wellness_score}/100",
        "diet": "🥗 **అనుకూలీకరించిన ఆహార ప్రణాళిక**:\n*   **అల్పాహారం**: బాదం, బెర్రీలతో కూడిన ఓట్ మీల్.\n*   **మధ్యాహ్న భోజనం**: గ్రిల్డ్ పనీర్/చికెన్ సలాడ్.\n*   **స్నాక్**: వాల్ నట్స్ మరియు పెరుగు.\n*   **రాత్రి భోజనం**: పప్పు సూప్ మరియు పచ్చని కూరగాయలు.",
        "workout": "🏃 **సిఫార్సు చేసిన వ్యాయామ ప్రణాళిక**:\n*   **కార్డియో**: వారానికి 3-4 రోజులు 30 నిమిషాలు వేగంగా నడవడం లేదా సైక్లింగ్.\n*   **స్ట్రెంగ్త్**: వారానికి 2 రోజులు స్క్వాట్స్ మరియు ప్లాంక్స్.",
        "stress": "🧘 **మానసిక ఒత్తిడి ఉపశమన చిట్కాలు**:\n*   స్క్రీన్ విరామ సమయంలో 3 నిమిషాల పాటు **4-7-8 బాక్స్ శ్వాస వ్యాయామం** చేయండి.\n*   5 నిమిషాల నడక విరామం తీసుకోండి.",
        "sleep": "🌙 **మంచి నిద్ర కోసం చిట్కాలు**:\n*   రోజుకు 7.5 - 8 గంటలు నిద్రపోండి.\n*   పడుకునే 45 నిమిషాల ముందు ఫోన్ లేదా స్క్రీన్ చూడకండి.",
        "greeting": "నమస్కారం! నేను మీ AI వెల్నెస్ కోచ్‌ని. ఈరోజు మీ ఆరోగ్య లక్ష్యాలలో నేను మీకు ఎలా సహాయపడగలను?",
        "motivation": "గుర్తుంచుకోండి: 'చేయని వ్యాయామం ఒక్కటే చెడ్డ వ్యాయామం.' ఉత్సాహంగా ఉండండి!",
        "water": "రోజుకు 2.5 - 3.0 లీటర్ల నీరు తాగడం వల్ల మానసిక ప్రశాంతత పెరుగుతుంది.",
        "no_profile": "మీకు ఇంకా ఆరోగ్య ప్రొఫైల్ నమోదు కాకపోలేదు. దయచేసి మొదట మీ ఆరోగ్య వివరాలను నమోదు చేయండి!"
    },
    "ta-IN": {
        "booking": "📅 உங்களுக்காக ஒரு மெய்நிகர் சுகாதார பரிசோதனை சந்திப்பை நான் திட்டமிட்டுள்ளேன்!\n\n**மருத்துவர்**: {doctor}\n**நேரம்**: {date_str}",
        "vitals": "🩺 **உங்கள் தற்போதைய சுகாதார சுயவிவரம்**:\n\n*   **BMI**: {bmi} ({bmi_category})\n*   **இதய துடிப்பு**: {heart_rate} bpm\n*   **மனஅழுத்தம்**: {stress_level}\n*   **சுகாதார ஆபத்து**: {health_risk_score}%\n*   **நல்வாழ்வு மதிப்பெண்**: {wellness_score}/100",
        "diet": "🥗 **பரிந்துரைக்கப்பட்ட உணவு திட்டம்**:\n*   **காலை உணவு**: ஓட்ஸ் மற்றும் பாதாம்.\n*   **மதிய உணவு**: காய்கறி சலாட் மற்றும் பருப்பு.\n*   **இரவு உணவு**: பருப்பு சூப் மற்றும் காய்கறிகள்.",
        "workout": "🏃 **உடற்பயிற்சி திட்டம்**:\n*   **கார்டியோ**: வாரத்திற்கு 3-4 நாட்கள் 30 நிமிடங்கள் நடைபயிற்சி.\n*   **வலிமை**: வாரத்திற்கு 2 நாட்கள் உடற்பயிற்சி.",
        "stress": "🧘 **மனஅழுத்த நிவாரணம்**:\n*   3 நிமிடங்கள் **4-7-8 மூச்சுப் பயிற்சி** செய்யுங்கள்.",
        "sleep": "🌙 **நல்ல தூக்கத்திற்கான வழிகாட்டுதல்**:\n*   இரவில் 7.5 - 8 மணி நேரம் தூங்குங்கள்.",
        "greeting": "வணக்கம்! நான் உங்கள் AI வெல்னஸ் கோச். இன்று உங்களுக்கு எவ்வாறு உதவ முடியும்?",
        "motivation": "தினமும் உடற்பயிற்சி செய்து ஆரோக்கியமாக இருங்கள்!",
        "water": "தினமும் 2.5 - 3.0 லிட்டர் தண்ணீர் குடியுங்கள்.",
        "no_profile": "தயவுசெய்து உங்கள் சுகாதார விவரங்களை பதிவு செய்யுங்கள்!"
    },
    "es-ES": {
        "booking": "📅 ¡He programado una cita de chequeo virtual para ti!\n\n**Doctor**: {doctor}\n**Hora**: {date_str}",
        "vitals": "🩺 **Resumen de tu perfil de salud activo**:\n\n*   **IMC**: {bmi} ({bmi_category})\n*   **Ritmo cardíaco**: {heart_rate} bpm\n*   **Nivel de estrés**: {stress_level}\n*   **Riesgo de salud**: {health_risk_score}%\n*   **Puntuación de bienestar**: {wellness_score}/100",
        "diet": "🥗 **Plan de nutrición personalizado**:\n*   **Desayuno**: Avena con almendras y frutos rojos.\n*   **Almuerzo**: Ensalada de pollo a la plancha o tofu con quinoa.\n*   **Cena**: Sopa de lentejas con verduras al vapor.",
        "workout": "🏃 **Plan de entrenamiento recomendado**:\n*   **Cardio**: 30 minutos de caminata rápida o ciclismo 3-4 días/semana.\n*   **Fuerza**: 2 días/semana de sentadillas y planchas.",
        "stress": "🧘 **Protocolo de alivio del estrés**:\n*   Practica la respiración 4-7-8 durante 3 minutos.",
        "sleep": "🌙 **Estrategia de higiene del sueño**:\n*   Duerme entre 7.5 y 8 horas por noche.",
        "greeting": "¡Hola! Soy tu entrenador de bienestar de IA. ¿Cómo puedo ayudarte hoy?",
        "motivation": "¡Recuerda: 'El único mal entrenamiento es el que no se hace!'",
        "water": "Bebe de 2.5 a 3.0 litros de agua al día.",
        "no_profile": "¡Aún no tienes un perfil de salud registrado!"
    },
    "fr-FR": {
        "booking": "📅 J'ai planifié un rendez-vous de bilan de santé virtuel pour vous !\n\n**Médecin**: {doctor}\n**Heure**: {date_str}",
        "vitals": "🩺 **Aperçu de votre profil de santé actif** :\n\n*   **IMC**: {bmi} ({bmi_category})\n*   **Fréquence cardiaque**: {heart_rate} bpm\n*   **Niveau de stress**: {stress_level}\n*   **Risque de santé**: {health_risk_score}%\n*   **Score de bien-être**: {wellness_score}/100",
        "diet": "🥗 **Plan de nutrition personnalisé** :\n*   **Petit déjeuner**: Flocons d'avoine aux amandes.\n*   **Déjeuner**: Salade de poulet grillé et quinoa.",
        "workout": "🏃 **Programme d'entraînement recommandé** :\n*   **Cardio**: 30 minutes de marche rapide 3-4 jours/semaine.",
        "stress": "🧘 **Gestion du stress au travail** :\n*   Pratiquez la respiration 4-7-8 pendant 3 minutes.",
        "sleep": "🌙 **Stratégie de sommeil optimale** :\n*   Visez 7,5 à 8 heures de sommeil par nuit.",
        "greeting": "Bonjour ! Je suis votre coach bien-être IA. Comment puis-je vous aider ?",
        "motivation": "Chaque petit choix sain compte !",
        "water": "Buvez 2,5 à 3,0 litres d'eau par jour.",
        "no_profile": "Veuillez d'abord enregistrer votre profil de santé !"
    },
    "de-DE": {
        "booking": "📅 Ich habe einen virtuellen Gesundheitscheck-Termin für Sie vereinbart!\n\n**Arzt**: {doctor}\n**Zeit**: {date_str}",
        "vitals": "🩺 **Ihre aktuelle Gesundheitsprofil-Übersicht**:\n\n*   **BMI**: {bmi} ({bmi_category})\n*   **Puls**: {heart_rate} bpm\n*   **Stresslevel**: {stress_level}\n*   **Gesundheitsrisiko**: {health_risk_score}%\n*   **Wellness-Punktzahl**: {wellness_score}/100",
        "diet": "🥗 **Personalisiertes Ernährungskonzept**:\n*   **Frühstück**: Haferflocken mit Mandeln.\n*   **Mittagessen**: Hähnchen- oder Tofu-Salat mit Quinoa.",
        "workout": "🏃 **Empfohlener Trainingsplan**:\n*   **Ausdauer**: 30 Minuten zügiges Gehen 3-4 Tage/Woche.",
        "stress": "🧘 **Stressbewältigung im Büro**:\n*   Üben Sie 3 Minuten lang die 4-7-8 Atemtechnik.",
        "sleep": "🌙 **Optimale Schlafhygiene**:\n*   Achten Sie auf 7,5 bis 8 Stunden Schlaf pro Nacht.",
        "greeting": "Hallo! Ich bin Ihr KI-Wellness-Coach. Wie kann ich Ihnen heute helfen?",
        "motivation": "Jeder gesunde Schritt zählt!",
        "water": "Trinken Sie täglich 2,5 bis 3,0 Liter Wasser.",
        "no_profile": "Bitte tragen Sie zuerst Ihr Gesundheitsprofil ein!"
    }
}

LANG_NAME_MAP = {
    "en-US": "English",
    "hi-IN": "Hindi (हिंदी)",
    "te-IN": "Telugu (తెలుగు)",
    "ta-IN": "Tamil (தமிழ்)",
    "es-ES": "Spanish (Español)",
    "fr-FR": "French (Français)",
    "de-DE": "German (Deutsch)"
}


def process_chatbot_query(message, user, language="en-US"):
    msg_lower = message.lower()
    
    # Save user message
    user_msg = ChatMessage(user_id=user.id, sender="user", message_text=message)
    db.session.add(user_msg)
    db.session.commit()
    
    lang_dict = MULTILINGUAL_INTENT_REPLIES.get(language)
    
    # 0. Check Steps or Water Goal-Logging Intents
    steps_match = re.search(r"\b(\d{1,3}(?:,\d{3})*|\d+)\s*steps\b", msg_lower)
    water_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:liters|litres|l)\b", msg_lower)
    
    is_logging = False
    reply = ""
    
    if steps_match and ("walk" in msg_lower or "log" in msg_lower or "today" in msg_lower or "add" in msg_lower or "run" in msg_lower):
        steps_val = int(steps_match.group(1).replace(",", ""))
        record = EmployeeHealth.query.filter_by(user_id=user.id).first()
        if record:
            record.daily_step_count = steps_val
            db.session.commit()
            reply = f"🏃 I have successfully logged **{steps_val:,} steps** directly into your active wellness record! Keep moving and staying active!"
            is_logging = True
        else:
            reply = lang_dict["no_profile"] if lang_dict else "You don't have a health profile logged yet. Please log your health metrics first under 'Health Data' in the sidebar!"
            is_logging = True
            
    elif water_match and ("drink" in msg_lower or "drank" in msg_lower or "log" in msg_lower or "water" in msg_lower or "add" in msg_lower):
        water_val = float(water_match.group(1))
        record = EmployeeHealth.query.filter_by(user_id=user.id).first()
        if record:
            record.daily_water_litres = water_val
            db.session.commit()
            reply = f"💧 I have successfully updated your daily water intake to **{water_val:.1f} Litres** directly in your active wellness record. Staying hydrated improves recovery!"
            is_logging = True
        else:
            reply = lang_dict["no_profile"] if lang_dict else "You don't have a health profile logged yet. Please log your health metrics first under 'Health Data' in the sidebar!"
            is_logging = True

    if is_logging:
        bot_msg = ChatMessage(user_id=user.id, sender="bot", message_text=reply)
        db.session.add(bot_msg)
        db.session.commit()
        return reply

    # Refined booking intent
    booking_keywords = [
        "book doctor", "book appointment", "book checkup", "schedule doctor", 
        "schedule appointment", "schedule checkup", "doctor visit", 
        "medical consult", "schedule a virtual checkup"
    ]
    is_booking = any(kw in msg_lower for kw in booking_keywords) or (
        ("book" in msg_lower or "schedule" in msg_lower) and 
        ("appointment" in msg_lower or "checkup" in msg_lower or "doctor" in msg_lower)
    )
    
    # 1. Appointment Booking Intent
    if is_booking:
        doctors = ["Dr. Gupta (General Vitals)", "Dr. Sharma (Cardio Specialist)", "Dr. Patel (Mental Coach)"]
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        times = ["9:30 AM", "11:00 AM", "2:30 PM", "4:00 PM"]
        
        doctor = random.choice(doctors)
        date_str = f"Next {random.choice(days)} at {random.choice(times)}"
        
        appointment = CheckupAppointment(
            user_id=user.id,
            doctor_name=doctor,
            appointment_date=date_str
        )
        db.session.add(appointment)
        db.session.commit()
        
        if lang_dict and "booking" in lang_dict:
            reply = lang_dict["booking"].format(doctor=doctor, date_str=date_str)
        else:
            reply = f"📅 I have scheduled a virtual health checkup appointment for you!\n\n**Doctor**: {doctor}\n**Time**: {date_str}\n\nIt has been logged in your appointments schedule panel."
        
    # 2. Vitals Intent
    elif ("bmi" in msg_lower or "my health" in msg_lower or "my vitals" in msg_lower or "risk" in msg_lower) and "schedule" not in msg_lower:
        record = EmployeeHealth.query.filter_by(user_id=user.id).first()
        if record:
            if lang_dict and "vitals" in lang_dict:
                reply = lang_dict["vitals"].format(
                    bmi=record.bmi,
                    bmi_category=record.bmi_category,
                    heart_rate=record.heart_rate,
                    stress_level=record.stress_level,
                    health_risk_score=record.health_risk_score,
                    wellness_score=record.wellness_score
                )
            else:
                reply = f"🩺 **Here is your active health profile overview**:\n\n" \
                        f"*   **BMI**: {record.bmi} ({record.bmi_category})\n" \
                        f"*   **Heart Rate**: {record.heart_rate} bpm\n" \
                        f"*   **Stress Level**: {record.stress_level}\n" \
                        f"*   **Calculated Health Risk**: {record.health_risk_score}%\n" \
                        f"*   **Calculated Wellness Score**: {record.wellness_score}/100\n\n" \
                        f"Let me know if you would like custom recommendations or want to schedule a checkup!"
        else:
            reply = lang_dict["no_profile"] if lang_dict else "You don't have a health profile logged yet. Please log your health metrics first under 'Health Data' in the sidebar!"
            
    # 3. LLM/NLP processing
    else:
        record = EmployeeHealth.query.filter_by(user_id=user.id).first()
        health_context = ""
        if record:
            health_context = f"User Health Context: BMI={record.bmi} ({record.bmi_category}), Stress={record.stress_level}, HR={record.heart_rate} bpm."
            
        target_lang_name = LANG_NAME_MAP.get(language, "English")
        lang_instruction = ""
        if language != "en-US":
            lang_instruction = f" CRITICAL MANDATORY INSTRUCTION: You MUST write your complete response 100% in {target_lang_name} language (using native {target_lang_name} script). Do not output any English."

        system_prompt = f"You are an expert AI Wellness & Health Coach for corporate employees. " \
                        f"Provide direct, highly encouraging, and accurate wellness advice. {health_context} " \
                        f"{lang_instruction} Keep your response concise and focused strictly on employee health."
                        
        try:
            url = "http://127.0.0.1:11434/api/generate"
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": "qwen2.5:0.5b",
                "prompt": f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{message}<|im_end|>\n<|im_start|>assistant\n",
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "stop": ["<|im_end|>", "<|endoftext|>"]
                }
            }
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                reply = response.json().get("response", "").strip()
            else:
                reply = ""
        except Exception:
            reply = ""
            
        if not reply:
            if any(w in msg_lower for w in ["diet", "food", "meal", "eat", "nutrition"]):
                if lang_dict and "diet" in lang_dict:
                    reply = lang_dict["diet"]
                else:
                    workout_diet = "Incorporate low-carbohydrate, high-protein meals with plenty of green vegetables." if record and record.bmi >= 25 else "Maintain balanced protein, whole grains, and healthy fats."
                    reply = f"🥗 **Tailored Wellness Diet Plan**:\n" \
                            f"*   **Breakfast**: Oatmeal with sliced almonds, chia seeds & berries.\n" \
                            f"*   **Lunch**: Grilled chicken/tofu salad with quinoa & olive oil dressing.\n" \
                            f"*   **Snack**: Handful of walnuts, Greek yogurt & 1 apple.\n" \
                            f"*   **Dinner**: Baked salmon/lentil soup with steamed broccoli & brown rice.\n" \
                            f"*   **Guideline**: {workout_diet}"
            elif any(w in msg_lower for w in ["workout", "exercise", "gym", "cardio", "fitness"]):
                if lang_dict and "workout" in lang_dict:
                    reply = lang_dict["workout"]
                else:
                    reply = f"🏃 **Recommended Active Workout Plan**:\n" \
                            f"*   **Cardio**: 30 minutes of brisk walking, cycling, or light jogging 3-4 days/week.\n" \
                            f"*   **Strength Work**: 3 sets of bodyweight squats, lunges, and 45-second core planks 2 days/week.\n" \
                            f"*   **Flexibility**: 10 minutes of post-workout hamstring and shoulder stretches."
            elif any(w in msg_lower for w in ["stress", "anxiety", "relax", "calm", "mindfulness"]):
                if lang_dict and "stress" in lang_dict:
                    reply = lang_dict["stress"]
                else:
                    reply = f"🧘 **Workplace Stress Relief Protocol**:\n" \
                            f"*   Practice **4-7-8 Box Breathing** for 3 minutes during screen breaks.\n" \
                            f"*   Take a 5-minute walking break and do gentle neck/shoulder rolls.\n" \
                            f"*   Sip warm herbal tea and practice 10-minute mindfulness sessions."
            elif any(w in msg_lower for w in ["sleep", "insomnia", "rest", "tired"]):
                if lang_dict and "sleep" in lang_dict:
                    reply = lang_dict["sleep"]
                else:
                    reply = f"🌙 **Optimal Sleep Hygiene Strategy**:\n" \
                            f"*   Aim for 7.5 - 8 hours of sleep per night to maximize physical recovery.\n" \
                            f"*   Avoid blue light screens at least 45 minutes before bedtime.\n" \
                            f"*   Keep your bedroom cool (around 20°C) and completely dark."
            elif "hello" in msg_lower or "hi" in msg_lower or "hey" in msg_lower:
                if lang_dict and "greeting" in lang_dict:
                    reply = lang_dict["greeting"]
                else:
                    reply = random.choice(WELLNESS_NLP_DICTIONARY["greeting"])
            elif "motivation" in msg_lower or "motivate" in msg_lower or "quote" in msg_lower:
                if lang_dict and "motivation" in lang_dict:
                    reply = lang_dict["motivation"]
                else:
                    reply = random.choice(WELLNESS_NLP_DICTIONARY["motivation"])
            elif "water" in msg_lower or "hydration" in msg_lower:
                if lang_dict and "water" in lang_dict:
                    reply = lang_dict["water"]
                else:
                    reply = WELLNESS_NLP_DICTIONARY["water"]
            elif "bmi" in msg_lower or "weight" in msg_lower:
                reply = WELLNESS_NLP_DICTIONARY["bmi_info"]
            else:
                reply = lang_dict["greeting"] if lang_dict else WELLNESS_NLP_DICTIONARY["default"]
                
    bot_msg = ChatMessage(user_id=user.id, sender="bot", message_text=reply)
    db.session.add(bot_msg)
    db.session.commit()
    
    return reply
