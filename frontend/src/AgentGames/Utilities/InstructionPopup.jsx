import React, { useState } from 'react';
import './css/instructions.css';

const InstructionPopup = ( {instructions='', homescreen = true}) => {
    const [isOpen, setIsOpen] = useState(false);

    const toggleDropdown = () => {
      setIsOpen(!isOpen);
    };
  
    return (
      <div className="instruction-container">
        <div className="instruction-header" onClick={toggleDropdown}>
          <span className="instruction-icon">ℹ️</span>
          <span className="instruction-text">Click to See Instructions Below</span>
          <span className={`arrow ${isOpen ? 'down' : 'up'}`}>&#9660;</span>
        </div>
        {isOpen ? ( homescreen ? (
                  <div className="instructions-inner-container">
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
        ) : (
          <div className="dropdown-content">
            <div className="instructions-inner-container" dangerouslySetInnerHTML={{ __html: instructions }}>
            </div>
            </div>
        )
        ) : null}
      </div>
    );
  };

export default InstructionPopup;
