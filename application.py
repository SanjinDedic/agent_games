import os

def run_game(code):
    
    try:
        simulation = GameSimulation()
        simulation.set_folder("test_classes")
        result = simulation.run_simulation_many_times(50, verbose=False)
        ranking = my_rank(result, data.team_name)
        os.remove('test_classes/'+filename)
        filepath = "classes/"+filename
        
    except Exception as e:
       
        result = {"Error": e}
        return result

    return {"my ranking":str(ranking) +"/10","games played": 50, "game_result": result}

