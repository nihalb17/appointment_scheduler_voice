"""Test script to verify the complete booking flow end-to-end."""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8020"

def test_booking_flow():
    """Test the complete booking flow."""
    session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("=" * 60)
    print("TESTING COMPLETE BOOKING FLOW")
    print("=" * 60)
    print(f"Session ID: {session_id}")
    print()
    
    # Step 1: Initial greeting
    print("Step 1: Sending initial greeting...")
    response = send_chat(session_id, "Hi")
    print(f"Bot: {response['reply']}")
    print()
    
    # Step 2: Request to book
    print("Step 2: Requesting to book...")
    response = send_chat(session_id, "I want to book an appointment")
    print(f"Bot: {response['reply']}")
    print(f"Intent: {response['intent']}")
    print()
    
    # Step 3: Provide topic
    print("Step 3: Providing topic...")
    response = send_chat(session_id, "KYC")
    print(f"Bot: {response['reply']}")
    print(f"Topic: {response['topic']}")
    print()
    
    # Step 4: Provide time slot
    print("Step 4: Providing time slot...")
    response = send_chat(session_id, "tomorrow 5 PM")
    print(f"Bot: {response['reply']}")
    print(f"Intent: {response['intent']}")
    print(f"Topic: {response['topic']}")
    print(f"Time Slot: {response['time_slot']}")
    print(f"Eligibility Status: {response['eligibility_status']}")
    print()
    
    # Check if we got a confirmation prompt
    if "shall i proceed" in response['reply'].lower():
        print("✓ Got confirmation prompt")
        
        # Step 5: Confirm booking
        print("\nStep 5: Confirming booking...")
        response = send_chat(session_id, "yes")
        print(f"Bot: {response['reply']}")
        print(f"Intent: {response['intent']}")
        print(f"Topic: {response['topic']}")
        print(f"Time Slot: {response['time_slot']}")
        print()
        
        # Check if booking was confirmed
        if response['intent'] == 'book_confirmed':
            print("✓ Booking confirmed by orchestrator")
            
            # Step 6: Execute the booking
            print("\nStep 6: Executing booking...")
            execution_result = execute_booking(session_id, response['topic'], response['time_slot'])
            print(f"Execution Result: {json.dumps(execution_result, indent=2)}")
            
            if execution_result.get('success'):
                print("\n" + "=" * 60)
                print("✓ BOOKING SUCCESSFUL!")
                print("=" * 60)
                print(f"Booking Code: {execution_result.get('result', {}).get('booking_code')}")
                print(f"Calendar Event: {execution_result.get('result', {}).get('calendar_event', {}).get('event_link', 'N/A')}")
                print(f"Google Doc: {execution_result.get('result', {}).get('google_doc', {}).get('doc_link', 'N/A')}")
                print(f"Email Sent: {execution_result.get('result', {}).get('email', {}).get('message_id', 'N/A')}")
                print(f"Sheets Log: Row {execution_result.get('result', {}).get('sheets_log', {}).get('row_number', 'N/A')}")
                return True
            else:
                print("\n✗ BOOKING FAILED")
                print(f"Error: {execution_result.get('message')}")
                return False
        else:
            print("✗ Did not get book_confirmed intent")
            return False
    else:
        print("✗ Did not get confirmation prompt")
        return False


def send_chat(session_id: str, message: str) -> dict:
    """Send a chat message."""
    response = requests.post(
        f"{BASE_URL}/chat",
        json={"session_id": session_id, "message": message}
    )
    if response.status_code != 200:
        print(f"Error response: {response.status_code}")
        print(f"Response body: {response.text}")
    response.raise_for_status()
    return response.json()


def execute_booking(session_id: str, topic: str, time_slot: str) -> dict:
    """Execute a booking."""
    response = requests.post(
        f"{BASE_URL}/execution/book",
        json={
            "session_id": session_id,
            "topic": topic,
            "time_slot": time_slot
        }
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    try:
        success = test_booking_flow()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
