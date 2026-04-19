Create an appointment scheduler voice/chat agent. It can create/remove a calendar event of a Mutual Fund Distributor.  
Create / Book an Appointment : When the user wants to book an appointment , the agent takes the appointment topic and the time slot from the user, checks the availability and, based on the availability, event to be created in the mutual fund distributors' calendar and booking code to be generated. Whenever an event is created, a Google Doc also must be created and in the title of the Google Doc should be the topic name along with the booking code and should be attached in the calendar event.




Remove/Cancel an Appointment : When the user wants to cancel an appointment, the agent takes the booking code and checks it and then cancels the event 


Whenever one of the above 2 actions happens, a mail is to be triggered by the mutual fund distributor. There should be a common sheet in which every action to be logged
The Calendar read , sending of mail, the Google Doc creation, the Google Sheets updation, and the calendar events add/edit/delete should happen via MCP. 
Before any of the calendar events is created or deleted, the agent should ask the user for the final approval before the changes 
The agent in no scenario should give investment advice to the users 
The agents should never take personal information from the users 
The appointment topic would be one of KYC/Onboarding, SIP/Mandates, Statements/Tax Docs, Withdrawals & Timelines, Account Changes/Nominee
Currently the reschedule option is not available. It should ask the user to cancel the existing booking first and then book a new appointment.
There would be an upload knowledge base option. Files uploaded will be referred by the agent for Checking for the slots 
