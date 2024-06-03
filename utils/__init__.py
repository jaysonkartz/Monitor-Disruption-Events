def datetimeToEnglish(datetime) -> str:
    """Converts a datetime object to a string in English.
    Example output: '2021-09-04 16:00:00' -> 'Saturday, September 4, 2021 4:00 PM'"""
    return datetime.strftime("%A, %B %d, %Y %I:%M %p")