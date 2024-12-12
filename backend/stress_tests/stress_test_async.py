import asyncio
import inspect
import time

import aiohttp


class Testing_Player:
    def make_decision(self, game_state):
        if len(game_state["players_banked_this_round"]) > 2:
            return "bank"
        return "continue"


async def make_request(session, url, data):
    async with session.post(url, json=data) as response:
        return response.status  # Use .status instead of .status_code


async def main():
    url = "https://vccfinal.net/agent_games/submit_agent"
    code = inspect.getsource(Testing_Player)
    number_of_tests = 250
    requests_per_second = (
        7  # 14 should have a 50% success rate, 7 should have a 99% success rate
    )
    responses = dict()

    start_t = time.time()

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(number_of_tests):
            data = {"team_name": "Sanjin", "password": "aaa", "code": code}
            task = asyncio.create_task(make_request(session, url, data))
            tasks.append(task)
            # Wait before sending next request
            await asyncio.sleep(1 / requests_per_second)

        results = await asyncio.gather(*tasks)

    for status_code in results:
        if status_code not in responses:
            responses[status_code] = 1
        else:
            responses[status_code] += 1

    elapse_t = time.time() - start_t
    print(f"Elapsed time: {elapse_t}")
    print(responses)
    success_rate = round(responses[200] / number_of_tests, 3) * 100
    print(f"Success rate: {success_rate}%")


asyncio.run(main())
