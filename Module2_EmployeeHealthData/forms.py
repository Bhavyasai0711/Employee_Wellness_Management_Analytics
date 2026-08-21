BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
SMOKING_OPTIONS = ["Never", "Occasionally", "Regularly", "Former"]
ALCOHOL_OPTIONS = ["Never", "Occasionally", "Regularly", "Former"]
EXERCISE_FREQUENCIES = ["Never", "1-2 days/week", "3-4 days/week", "5+ days/week", "Daily"]
STRESS_LEVELS = ["Low", "Moderate", "High", "Severe"]
BMI_CATEGORIES = ["Underweight", "Normal", "Overweight", "Obese"]


def health_form_options():
    return {
        "blood_groups": BLOOD_GROUPS,
        "smoking_options": SMOKING_OPTIONS,
        "alcohol_options": ALCOHOL_OPTIONS,
        "exercise_frequencies": EXERCISE_FREQUENCIES,
        "stress_levels": STRESS_LEVELS,
        "bmi_categories": BMI_CATEGORIES,
    }
