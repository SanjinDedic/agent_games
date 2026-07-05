import BreakthroughFeedback from './BreakthroughFeedback';
import BreakthroughResultsDisplay from './BreakthroughResultsDisplay';

export default {
  name: 'breakthrough',
  displayName: 'Breakthrough',
  description:
    'Program a dot to sprint past a defender to the right edge — or hunt the runner down. Simultaneous moves, limited boost jumps, pure mind-games.',
  shortDescription:
    'Attacker vs defender pursuit duel on a 100x100 grid.',
  thumbnail: 'games/breakthrough.png',
  featured: false,
  order: 8,
  Feedback: BreakthroughFeedback,
  ResultsDisplay: BreakthroughResultsDisplay,
};
