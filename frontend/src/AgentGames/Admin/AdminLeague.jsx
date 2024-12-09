import './css/adminleague.css';
import React, { useEffect } from 'react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import ResultsDisplay from '../Utilities/ResultsDisplay';
import FeedbackSelector from '../Utilities/FeedbackSelector';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import moment from 'moment-timezone';
import AdminLeagueCreation from './AdminLeagueCreation';
import AdminLeagueTeams from './AdminLeagueTeams';
import AdminLeagueSimulation from './AdminLeagueSimulation';
import AdminLeaguePublish from './AdminLeaguePublish';
import CustomRewards from './CustomRewards';
import { useDispatch, useSelector } from 'react-redux';
import { setCurrentLeague, setLeagues, updateExpiryDate,setCurrentSimulation, setResults, clearResults } from '../../slices/leaguesSlice';
import { checkTokenExpiry } from '../../slices/authSlice';

function AdminLeague() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const currentLeague = useSelector((state) => state.leagues.currentLeague);
  const allLeagues = useSelector((state) => state.leagues.list);
  const allSimulations = useSelector((state) => state.leagues.currentLeagueResults);
  const currentSimulation = useSelector((state) => state.leagues.currentLeagueResultSelected);
  const accessToken = useSelector((state) => state.auth.token);
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);
  
  moment.tz.setDefault("Australia/Sydney");

  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || currentUser.role !== "admin" || tokenExpired) {
      // Redirect to the home page if not authenticated
      navigate('/Admin');
    }
    
  }, [navigate]);

  const fetchAdminLeagues = () => {

    fetch(apiUrl + '/get_all_admin_leagues')
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          dispatch(setLeagues(data.data.admin_leagues));

        } else if (data.status === "failed") {
          toast.error(data.message)
        } else if (data.detail === "Invalid token") {
          navigate('/Admin');
        }
      })
      .catch(error => console.error('Error fetching options:', error));
    

  }

  useEffect(() => {
    fetchAdminLeagues();
  }, []);

  useEffect(() => {
    if (currentLeague?.name) {
      fetch(`${apiUrl}/get_all_league_results`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ name: currentLeague.name })
      })
        .then(response => response.json())
        .then(data => {
          console.log(data);
          if (data.status === "success") {
            if (data.data.all_results.length == 0) {
              dispatch(clearResults());
              toast.error("No results in the selected League")
            }

            else {
              dispatch(setResults(data.data.all_results));
            }

          } else if (data.status === "failed") {
            toast.error(data.message);
            dispatch(clearResults());
          } else if (data.detail === "Invalid token") {
            navigate('/Admin');
          }
        })
        .catch(error => console.error('Error fetching league results:', error));
      }
  }, [currentLeague]);

  const handleDropdownChange = (event) => {
    
    dispatch(setCurrentLeague(event.target.value));
    
  };

  const handletableDropdownChange = (event) => {
    dispatch(setCurrentSimulation(event.target.value));

  };



  const handleExpiryDateChange = (date) => {

    // Update the date in the database through the API
    const formattedDate = date.toISOString(); // Format the date as needed for your API
    fetch(`${apiUrl}/update_expiry_date`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ date: formattedDate, league: currentLeague.name }),
    })
      .then(response => response.json())
      .then(data => {

        if (data.status === "success") {
          dispatch(updateExpiryDate({ name: currentLeague.name, expiry_date: formattedDate}));
          toast.success(data.message);
          
        } else if (data.status === "failed") {
          toast.error(data.message)
        }
      })
      .catch(error => {
        console.error('Error updating date:', error);
      });
  };



  return (
    <>
      <div className="main-container">
        <h1>LEAGUE SECTION</h1>
        {currentLeague &&
        <select onChange={handleDropdownChange} value={currentLeague.name}>
          {allLeagues.map((league, index) => (
            <option key={index} value={league.name} style={{ color: moment().isBefore(moment(league.expiry_date)) ? 'green' : 'red' }}>
              {moment().isBefore(moment(league.expiry_date)) ? '🟢' : '🔴'} {league.name} ({league.game})
            </option>
          ))}
        </select>
        }

      </div>
      <div className='panel-container'>

        <div className='left'>
          <div className="output-container">
            {allSimulations &&
              <select onChange={handletableDropdownChange}>
                {allSimulations.map((option, index) => (
                  <option key={index} value={option.timestamp}>
                    {new Date(option.timestamp).toLocaleString()}
                  </option>
                ))}
              </select>
            }
            <br></br>
            {currentSimulation && (
              currentSimulation.feedback ? (
                <ResultsDisplay
                  data={currentSimulation}
                  highlight={false}
                  data_message={currentSimulation.message}
                  tablevisible={false}
                />
              ) : (
                <ResultsDisplay
                  data={currentSimulation}
                  highlight={false}
                  data_message={currentSimulation.message}
                  tablevisible={true}
                />
              )
              )}
            {currentSimulation?.feedback && <FeedbackSelector feedback={currentSimulation.feedback} />}
          </div>
          {currentLeague && <AdminLeagueTeams selected_league_name={currentLeague.name} />}
        </div>
        <div className='right'>
        {currentLeague && <AdminLeagueSimulation selected_league_name={currentLeague.name} />}
          <CustomRewards/>
          {currentLeague && currentSimulation &&  <AdminLeaguePublish simulation_id={currentSimulation.id} selected_league_name={currentLeague.name} />}
          <h2 style={{ marginTop: '20%' }}>Expiry Date Picker</h2>
          {currentLeague && 
          <DatePicker
            selected={currentLeague.expiry_date}
            onChange={handleExpiryDateChange}
            dateFormat="dd/MM/yyyy"
            placeholderText="Select a date"
            id="date-picker"
          />
          }
        </div>

      </div>
      <AdminLeagueCreation />

    </>
  );
}

export default AdminLeague;
