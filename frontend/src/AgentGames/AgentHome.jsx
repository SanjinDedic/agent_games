import React, { useState,useEffect } from 'react';
import { Link } from 'react-router-dom';
import './css/home.css';

const API_URL = process.env.REACT_APP_API_URL;

function AgentHome() {
    const [signupLink, setSignupLink] = useState('');
    const [leaguename, setLeagueName] = useState('');
    const [shake, setShake] = useState(false);

    const handleButtonClick = async () => {
        if (!leaguename.trim()) {
            setShake(true);
            setTimeout(() => setShake(false), 1000); // Reset shake after 1 second
            }
        
      try {
        const response = await fetch(API_URL+'/league_create', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            'name': leaguename
          }),
        });
  
        const data = await response.json();
        if (response.ok) {
          const uniqueText = data.link;
          setSignupLink(uniqueText);
        } else {
          throw new Error('Failed to generate link');
        }
      } catch (error) {
        console.error('Error:', error);
      }
      
    };
  
    return (
      <div className='flex-container'>
        <div className="instructions-container">
      <h1>Competition Instructions</h1>
      <ol>
          <li>
              <strong>Login Process</strong>
              <p>Click on the <b>Game Submission</b> option in the navbar to log in.</p>
          </li>
          <li>
              <strong>League Selection</strong>
              <p>Once logged in, select your league from the dropdown menu. Assign yourself to the league and click sign up for code submission.</p>
          </li>
          <li>
              <strong>Code Submission Page</strong>
              <p>Add your algorithm code on the submission page.</p>
              <strong>Important:</strong>
              <ul className='circle-points'>
                  <li> Do not include libraries that may break. Such submissions will be rejected, and no results will be displayed. Only return <code>bank</code> and <code>continue</code>; other returns will not be accepted.</li>
                  <li>Ensure your algorithm executes in under 3 seconds, or it will be rejected.</li>
              </ul>
          </li>
          <li>
              <strong>Submission Limit</strong>
              <p>You are allowed up to 3 submissions per minute. Exceeding this limit will result in an error.</p>
          </li>
          <li>
              <strong>Results and Rankings</strong>
              <p>If your algorithm is correct, you will see the results against bots upon submission. Once your code is submitted and simulations are executed by the teacher, you can view your results on the rankings page.</p>
          </li>
          <li>
              <strong>Viewing Rankings</strong>
              <p>On the rankings page, you can view the updated results as assigned by the teachers.</p>
          </li>
          <li>
              <strong>Support</strong>
              <p>If you have any questions, please contact an administrator or a teacher.</p>
          </li>
      </ol>
  </div>

        {/* <input
            type="text"
            value={leaguename}
            onChange={(e) => setLeagueName(e.target.value)}
            className={shake ? 'shake' : ''}
          />
        <button onClick={handleButtonClick}>Generate League</button>
        {signupLink && (
          <div>
            <Link Link to={`/AgentGames/signup/${signupLink}`}>Sign Up Here</Link>
          </div>
        )} */}
      </div>
    );
}

export default AgentHome;