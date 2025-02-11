import csv
import os
import re
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def parse_time_input(time_input):
    """Normalize and parse time input with multiple formats."""
    time_input = re.sub(r'[\.;]', ':', time_input)
    time_input = re.sub(r'[,]', '.', time_input)
    time_input = time_input.strip()

    # Convert input like '2000' to '20:00'
    if len(time_input) == 4 and time_input.isdigit():
        time_input = f"{time_input[:2]}:{time_input[2:]}"
    
    try:
        return datetime.strptime(time_input, "%H:%M")
    except ValueError:
        logging.error(f"Invalid time format: {time_input}. Please use HH:MM, HH.MM, HH;MM, or HHMM format.")
        return None

def calculate_duration(start_time, end_time):
    """Calculate duration with advanced rounding and cost calculation."""
    duration = end_time - start_time
    if duration.total_seconds() < 0:
        logging.error("End time must be after start time.")
        return None

    total_minutes = duration.total_seconds() / 60
    hours = total_minutes // 60
    minutes = total_minutes % 60

    # Rounding logic
    if minutes <= 19:
        rounded_hours = int(hours)
        rounded_minutes = 0
    elif 20 <= minutes <= 49:
        rounded_hours = int(hours)
        rounded_minutes = 30
    else:
        rounded_hours = int(hours) + 1
        rounded_minutes = 0

    # Decimal hours based on ROUNDED time
    decimal_hours = rounded_hours + (0.5 if rounded_minutes == 30 else 0)

    # Cost calculation
    cost = (rounded_hours * 220) + (rounded_minutes // 30 * 110)

    logging.info(f"Duration calculated: {hours}h {minutes}m | Rounded: {rounded_hours}h {rounded_minutes}m")

    return {
        "start_time": start_time.strftime("%H:%M"),
        "end_time": end_time.strftime("%H:%M"),
        "original_hours": int(hours),
        "original_minutes": int(minutes),
        "rounded_hours": rounded_hours,
        "rounded_minutes": rounded_minutes,
        "decimal_hours": round(decimal_hours, 1),
        "cost": cost,
        "formatted_cost": f"${cost:.2f}"
    }

def display_sessions(sessions):
    """Display sessions in a formatted, readable manner."""
    print("\n{:<5} {:<10} {:<10} {:<15} {:<15} {:<15} {:<10}".format(
        "No.", "Start", "End", "Original Time", "Rounded Time", "Decimal Hours", "Cost"))
    print("-" * 85)
    for i, session in enumerate(sessions, 1):
        print("{:<5} {:<10} {:<10} {:<15} {:<15} {:<15} {:<10}".format(
            str(i)+".", 
            session['start_time'], 
            session['end_time'], 
            f"{session['original_hours']}h {session['original_minutes']}m",
            f"{session['rounded_hours']}h {session['rounded_minutes']}m",
            session['decimal_hours'],
            session['formatted_cost']
        ))

def get_multiple_session_details():
    """Interactive method to get multiple session details."""
    sessions = []
    while True:
        start_input = input("Enter start time (or 'q' to quit adding): ")
        if start_input.lower() in ['q', 'quit']:
            break

        end_input = input("Enter end time: ")

        start_time = parse_time_input(start_input)
        end_time = parse_time_input(end_input)

        if not start_time or not end_time:
            continue

        # Handle overnight sessions
        if end_time < start_time:
            end_time += timedelta(days=1)

        duration = calculate_duration(start_time, end_time)
        if duration:
            sessions.append(duration)
            print(f"Session added: {duration['start_time']} - {duration['end_time']}, Cost: {duration['formatted_cost']}")

    return sessions

def manage_sessions(sessions):
    """Comprehensive session management interface."""
    while True:
        display_sessions(sessions)
        print("\nOptions:")
        print("1. Add Session(s)")
        print("2. Edit Session")
        print("3. Remove Session")
        print("4. Finish and Save")

        choice = input("Enter your choice (1-4): ")

        if choice == '1':
            # Add Sessions
            new_sessions = get_multiple_session_details()
            if new_sessions:
                sessions.extend(new_sessions)
                logging.info(f"Added {len(new_sessions)} new session(s).")

        elif choice == '2':
            # Edit Session
            if not sessions:
                print("No sessions to edit.")
                continue

            try:
                index = int(input("Enter the session number to edit: ")) - 1
                if 0 <= index < len(sessions):
                    print("Current Session:", sessions[index])
                    start_input = input("Enter new start time: ")
                    end_input = input("Enter new end time: ")

                    start_time = parse_time_input(start_input)
                    end_time = parse_time_input(end_input)

                    if start_time and end_time:
                        # Handle overnight sessions
                        if end_time < start_time:
                            end_time += timedelta(days=1)

                        new_session = calculate_duration(start_time, end_time)
                        if new_session:
                            sessions[index] = new_session
                            logging.info("Session updated successfully.")
                else:
                    print("Invalid session number.")
            except ValueError:
                print("Please enter a valid number.")

        elif choice == '3':
            # Remove Session
            if not sessions:
                print("No sessions to remove.")
                continue

            try:
                indices = input("Enter session numbers to remove (comma-separated): ")
                to_remove = [int(x.strip()) - 1 for x in indices.split(',')]
                
                # Remove in reverse to maintain index integrity
                for index in sorted(to_remove, reverse=True):
                    if 0 <= index < len(sessions):
                        del sessions[index]
                        logging.info(f"Removed session {index + 1}")
            except ValueError:
                print("Invalid input. Please enter valid session numbers.")

        elif choice == '4':
            break

    return sessions

def save_sessions_to_csv(sessions, filename):
    """Save sessions to a CSV file with comprehensive error handling."""
    try:
        with open(filename, 'w', newline='') as file:
            # Include 'cost' in the fieldnames list
            fieldnames = ['start_time', 'end_time', 'original_hours', 'original_minutes', 
                          'rounded_hours', 'rounded_minutes', 'decimal_hours', 'formatted_cost', 'cost']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            
            # Ensure all fields are written properly
            for session in sessions:
                session_copy = session.copy()  # To prevent mutation
                session_copy['cost'] = float(session_copy.get('cost', 0))  # Convert to float
                writer.writerow(session_copy)
        
        # Convert cost values to floats before summing
        total_cost = sum(float(session.get('cost', 0)) for session in sessions)
        logging.info(f"Sessions saved to {filename}")
        print(f"Total Cost: ${total_cost:.2f}")
    except Exception as e:
        logging.error(f"Error saving sessions: {e}")

def main():
    print("Time Tracking and Billing System")
    sessions = []

    filename = input("Enter filename to save/load sessions (without .csv): ") + ".csv"
    
    # Load existing sessions if file exists
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as file:
                reader = csv.DictReader(file)
                sessions = list(reader)
                logging.info(f"Loaded {len(sessions)} existing sessions.")
        except Exception as e:
            logging.error(f"Error loading existing sessions: {e}")

    # Manage sessions
    final_sessions = manage_sessions(sessions)

    # Save sessions
    save_sessions_to_csv(final_sessions, filename)

if __name__ == "__main__":
    main()