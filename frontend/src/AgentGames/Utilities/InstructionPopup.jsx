import React, { useState } from 'react';
import PureMarkdown from './PureMarkdown';

const InstructionPopup = ({ instructions = '', homescreen = true }) => {
  const [isOpen, setIsOpen] = useState(false);

  const defaultInstructions = `# Competition Instructions

1. **Login Process**
   - Click on the **Game Submission** option in the navbar to log in.

2. **League Selection**
   - Once logged in, select your league from the dropdown menu.
   - Assign yourself to the league and click sign up for code submission.

3. **Code Submission Page**
   - Add your algorithm code on the submission page.
   
   **Important:**
   - Do not include libraries that may break. Such submissions will be rejected, and no results will be displayed.
   - Only return \`bank\` and \`continue\`; other returns will not be accepted.
   - Ensure your algorithm executes in under 3 seconds, or it will be rejected.

4. **Submission Limit**
   - You are allowed up to 3 submissions per minute.
   - Exceeding this limit will result in an error.

5. **Results and Rankings**
   - If your algorithm is correct, you will see the results against bots upon submission.
   - Once your code is submitted and simulations are executed by the teacher, you can view your results on the rankings page.

6. **Viewing Rankings**
   - On the rankings page, you can view the updated results as assigned by the teachers.

7. **Support**
   - If you have any questions, please contact an administrator or a teacher.`;

  const content = homescreen ? defaultInstructions : instructions;

  return (
    <div className="min-w-[800px] mx-auto mb-8 rounded-lg shadow-md border border-primary/30 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 bg-primary text-white transition-colors duration-200 hover:bg-primary-hover"
      >
        <div className="flex items-center space-x-2">
          <span className="text-xl">ℹ️</span>
          <span className="text-lg font-medium">Click to See Instructions Below</span>
        </div>
        <span
          className={`transform transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          aria-hidden="true"
        >
          ▼
        </span>
      </button>

      {isOpen && (
        <div className="bg-white">
          <div className="p-8">
            <PureMarkdown content={content} />
          </div>
        </div>
      )}
    </div>
  );
};

export default InstructionPopup;