# Personal AI Assistant - Project Requirements Template

Please fill out this template to help define the scope, features, and constraints of your AI assistant. The more detailed you are, the better I can help you build exactly what you want!

## 1. Core Identity & Personality
- **Name of the Assistant:** 
- **Tone/Personality:** casual, humorous, can push a bit, isn't afraid to call me out for not doing my things. However it should also empathize.
- **Primary Goal:** Keep me organized, push me to achieve my goals, handle scheduling, understands my mental state and what I need.

## 2. Knowledge & Memory
- **What should the agent know about you?** I am a 28 year old man living in the netherlands. I like personal health and fitness and am immersed in the longevity community. My main inspiration when it comes to longevity is Bryan Johnson, whatever he does I also try to do to a degree. This means going to bed on time, working out, eathing healthy. I am very healthy and strong. I wear a whoop which collects data on me, according to it im 24 years old.
I work for ABN AMRO, a dutch bank. I do data management as a data steward. this is a new role for me so there is a lot to learn. I find it hard to keep my work organized, i have tried many things but all the systems on my abn system dont work too well. maybe you can help with this.
I have functional autism and ADHD, i think to a light degree but adhd sometimes gets in the way. for autism i have fugured out systems and its not problematic at all.
I have bursts of interests, for a few months I have 1 hobby and then later it will be something else. this means I do a lot of different things wich I also enjoy. I see this as a superpower but it is sometimes hard for me to find consistency.
- **How will the agent store information?** Local files for now
- **How long should it remember things?** very long time, I want it to know as much as possible. possibly only delete unimportant things to keep context low.

## 3. Key Features & Capabilities
### Calendar & Scheduling (Google Calendar Integration)
- [ ] Read existing events
- [ ] Create new events
- [ ] Modify/Delete events
- **Specific scheduling rules:** No im am very flexible with my scheduling, for example i like to go running once a week when the weather is nice. possibly the app could integrate with the weather to plan this? Also when I go to the gym i train whichever muscles aren't sore, the app could plan this a bit better for me.

### Task Management (Projects & Habits)
- **How should it track projects?**  with a Simple to-do list and milestone tracking. when things are broken up into small tasks for me that helps a lot. the manager should split the projects into simple tasks that I can do and tell me each time what to do. The same could be done for things I have to do for work.
- **What habits should it enforce or track?**
The main thing is that I need to spend time doing productive things instead of doing nothing watching tv. so anything could be good to do. I already go to bed on time and work out so these should be tracked but they are not important to focus on. focus mainly on giving me a healthy life balance, where I get a lot of work done but where also time for leisure is planned in my agenda.

### Interactions
- **How will you communicate with it?** 
  - [ ] Text (Chat Interface / Web UI)
  - [ ] Voice (Speech-to-Text / Text-to-Speech)
  - possible an integration into some chat app that I can talk to.

## 4. Technical Stack Preferences
*(If you're not sure about these, I can recommend the best options!)*
do the best options
- **Frontend / UI:** (e.g., Next.js, React, simple HTML/CSS, or no UI/just terminal?)
- **Backend:** (e.g., Node.js/Express, Python/FastAPI?)
- **Database:** (e.g., PostgreSQL, MongoDB, local JSON?)
- **AI Model / Brain:** (e.g., Google Gemini API for processing natural language)
- **Authentication:** locally for me

## 5. Security & Privacy
- **Google Calendar Permissions:** (Requires OAuth2 setup - how comfortable are you with configuring Google Cloud API keys?)
this is no problem
- **Data Privacy:** Should data be strictly stored locally on your machine for now

## 6. Milestones (How we will build it)
- **Phase 1:** Basic Chat Interface + AI Integration (Talking to the agent)
- **Phase 2:** Memory System (Agent remembers facts about you)
- **Phase 3:** Google Calendar Integration (Agent can read/write to your calendar)
- **Phase 4:** Proactive Planning (Agent schedules tasks/gym based on logic)

---
*Once you fill this out or provide some initial thoughts on these points, we can start planning the technical architecture!*
