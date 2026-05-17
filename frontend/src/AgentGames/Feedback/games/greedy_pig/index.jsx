import GreedyPigFeedback from './GreedyPigFeedback';

export default {
  name: 'greedy_pig',
  displayName: 'Greedy Pig',
  description:
    'A strategic game of risk and reward where players must decide when to bank their points or continue rolling.',
  shortDescription: 'A risk/reward dice game. When do you bank your points?',
  thumbnail: 'games/greedy_pig.png',
  featured: true,
  order: 1,
  Feedback: GreedyPigFeedback,
  ResultsDisplay: null,
};
