from player_base import Player
import openai

#WARNING DO NOT RUN THIS AGENT with more than 10 sims, API costs will be too high

class AIPlayer(Player):
    def make_decision(self, game_state):
        #basically don't run this agent unless you have an API key
        if openai.api_key == 'INSERT YOUR KEY HERE':
            return 'bank'
        decision = self.openai_make_decision(game_state)
        return decision

    @staticmethod
    def openai_make_decision(game_state: dict) -> str:
        state_str = "\n".join(f"{key}: {value}" for key, value in game_state.items())
        prompt = (f"Here is the current game state:\n{state_str}\n"
                  "Based on this state, should the agent 'bank' the money or 'continue' playing?")
        
        try:
            # Use a standard GPT-4 model identifier here, such as 'text-davinci-003'
            response = openai.Completion.chat.create(
                engine="gpt-4-1106-preview",  # example model identifier
                prompt=prompt,
                max_tokens=50
            )
            decision = response.choices[0].text.strip().lower()
            return 'bank' if 'bank' in decision else 'continue'
        except Exception as e:
            print(f"An error occurred: {e}")
            return 'continue'

# Set your OpenAI API key
openai.api_key = 'INSERT YOUR KEY HERE'