def calculate_user_achievements(record):
    achievements = []
    if record:
        if record.wellness_score >= 80:
            achievements.append("Reached an excellent wellness score of 80 or higher")
        if record.daily_step_count and record.daily_step_count >= 4000:
            achievements.append("Reached the 4,000 daily step milestone")
        if record.daily_water_litres >= 2.5:
            achievements.append("Reached the daily hydration target")
        if record.sleep_hours >= 7.5:
            achievements.append("Reached the recommended sleep target")
        if record.attendance_percentage >= 95:
            achievements.append("Maintained 95%+ attendance consistency")
    return achievements
