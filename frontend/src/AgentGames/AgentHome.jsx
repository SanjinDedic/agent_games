import React, { useState,useEffect } from 'react';
import PureMarkdown from './Utilities/PureMarkdown';

function AgentHome() {
    const content = `# Introducing the Agent Games Competition at the Victorian Coding Challenge!

Are you ready to put your coding skills to the ultimate test? Welcome to the **Agent Games**, a thrilling competition that's part of the Victorian Coding Challenge where teams and individual coders design intelligent agents to compete against each other!

## About the Agent Games

In the Agent Games, participants will develop and submit their own code to control agents within a game environment. These agents will autonomously make decisions and take actions to outperform opponents in a strategic and dynamic setting.

## How It Works

- **Game Overview**: The competition revolves around a game where your agent competes against others. The specifics of the game mechanics are detailed in our instruction video.

- **Code Submission**: Write code that dictates your agent's behavior. Your agent should be able to analyze the game state and make optimal decisions.

- **Competition**: Agents will be matched against each other, and their performance will be evaluated based on predefined criteria such as efficiency, strategy, and success rate.

## Getting Started

1. **Watch the Instruction Video Below**: To understand the game rules and how to develop your agent, watch the instruction video provided below. This video offers a comprehensive guide to the competition.

   <!-- Instruction Video -->
   <video width="800px" controls>
     <source src="GREEDY_PIG_INTRO.mp4" type="video/mp4">
     Your browser does not support the video tag.
   </video>

2. **Set Up Your Development Environment**: Ensure you have all the necessary tools and libraries installed to start coding your agent.

3. **Design and Code Your Agent**: Develop your agent's strategy and implement it in code. Think creatively and strategically!

4. **Test Your Agent**: Before submission, test your agent thoroughly to make sure it behaves as expected in various scenarios.

## Submission Guidelines

- **Format**: Submit your code in the specified programming language and format as outlined in the competition rules.

- **Deadline**: All code submissions must be received by the competition deadline. Late entries may not be accepted.

- **Submission Portal**: Upload your agent's code through the official submission portal on our website.

## Competition Rules

- **Original Work**: Your submission must be your own work. Collaboration is allowed within teams but not between different teams.

- **No Malicious Code**: Your code must not contain any harmful or disruptive elements.

- **Adherence to Game Rules**: Agents must operate within the rules specified in the instruction video and official documentation.

## Prizes and Recognition

Winners will receive exciting prizes and will be recognized at the Victorian Coding Challenge awards ceremony. This is your chance to shine and showcase your coding talents!

---

**Are you up for the challenge? Start coding your agent today and see if you have what it takes to emerge victorious!**

---

Good luck, and may the best agent win!
`
  
    return (
      <div style={{display:'flex'}}>
      <PureMarkdown content={content}/>
      </div>
    );
}

export default AgentHome;