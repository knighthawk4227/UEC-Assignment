# UEC-Assignment
UEC Assignment to create an interface for Teams to review high quantities of data by grouping actions as they are seen together.

## How to run:
- Data file on same dir level as import.py
  
- Add env variables
  - File name without path
  - gap you want to set for doc search
  - "dbname".db
- create a python env
  - pip install -r requirements.txt
- pythton import.py
- python -m flask --app app run --port {port #}
- open url displayed in terminal

### grouping approach, the alternatives you considered and why you chose this one:
- #### Rows are grouped by user and context. Within that, rows are sorted by time, and a new group starts whenever more than 5 minutes have passed since the previous row. 
### some alternatives I thought of initially looking at the data
  - Originally I thought of sorting it by just record ID's but I realized that maybe inforamtion being changed on a record might be not the same action necessarily and it may produce too many or too few rows depending on the # of record ID's or names
    
  -  This still didn't work well for bulk changes. Mass updates, CSV imports and scripts (many of which run overnight) touch many record IDs at once, so a single action would be split into hundreds of groups
    
  - I did consider the idea of grouping by mostly record names as well since there was only around 8,000 unique record names but I also didn't want to risk the possibility of records being changed months apart be something that doesn't need to be grouped in one.
### Why I chose this approach
- The reason I chose the method I did was it was able to encapsulate the Changes made to different records but also keep the ones that are not as related to be in different groups and I felt this way seperated them as much as I could (looking back adding record type definitely would have helped)

### Where it breaks down
- The bulk runs make very large groups
  - Some of the mass updates and scripts run on a lot of files so these all end up getting put in the same group

- Because I didn't use record type it some groups are bigger than they need to be
  - Since I did not implement the record_type it ends up putting more things into a group than need be 
### Stack:
#### Python 
  - pandas makes it simple to read the spreadsheet, clean it up and load it into a database. Loading and parsing data is the area I have the least experience in, so I wanted the most straightforward tools for that part. Stack overflow for reading xlsx also uses pandas
#### Flask 
  - Since I was already using python I thought it would be easy to just setup some routes and return the response of running SQL commands
#### HTML
  - HTML just vanilla mostly for time and ease of understanding
#### sqlite
- Single file is easy for project and someone doesn't need to setup postgres server or have a whole docker container setup just to run their own postgres server

what the interface does and the main design decisions
- The interface takes all the groups and displays them via risk.
  - The way I determined if something is risky is mostly doing changing of sensitive data,
    - if it is changing passwords or has bank info then it would be high risk
    - Creating a user, changing a script, or blank might be medium
    - Low would just have none of the above in it
      
- it displays groups
  - you can press on a group id to see the rows in that group
  
- You can Set a status to a group
  - Approve
  - Reject
  - I wanted to add a review by manager but did not get the time

### Assumptions I made:
- I assumed the the name of records may not be extremely useful in terms of grouping
- Grouping was not just supposed to be all Id's in one group or all Records with the same name in one group
- The way someone is going to be approving or denying these would be more focused on actions done near in date therefore record names would not be extremely useful
 
- Questions I would have asked
  - Information to display to person looking at groupings like should they see every column or are they mostly going to be reviewing specific columns more often than not
  - Should I have edge cases like putting all banking information, changes to a line on transaction into one group.
  - Would the names and/or ID's of records be useful for grouping (would we want to have groups of changes done to just one record across the entire data not requiring date)
### limitations, and what I'd do next:
- I would probably add record type into the grouping
  - looking at a lot of the data record type is very consistent and adding I feel would add more accuracy on the grouping for what someone would want to review.
  
- record name (maybe for specific contexts)
- The Frontend
  - Basic html for it and got an AI to generate it based off a drawing I made
  - If I were to redo it I would probably use something with Javascript and react to allow for colour changes and button presses that don't refresh the page everytime
  - Add filtering
  - The ability to change the group a row is in
  - mass approval (checkable boxes and just one approve reject button)
  
