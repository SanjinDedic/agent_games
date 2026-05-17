import Lineup4Feedback from './Lineup4Feedback';
import Lineup4ResultsDisplay from './Lineup4ResultsDisplay';

export default {
  name: 'lineup4',
  displayName: 'Lineup4',
  description:
    'Program an agent to play the classic Connect Four game, requiring spatial reasoning and forward planning.',
  shortDescription:
    'The strategic game of connecting four pieces in a row.',
  thumbnail: 'games/lineup4.png',
  featured: true,
  order: 3,
  Feedback: Lineup4Feedback,
  ResultsDisplay: Lineup4ResultsDisplay,
};
