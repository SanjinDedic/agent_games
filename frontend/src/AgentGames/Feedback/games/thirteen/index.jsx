import ThirteenFeedback from './ThirteenFeedback';
import ThirteenResultsDisplay from './ThirteenResultsDisplay';
import sampleFeedback from './sample_feedback.json';

export default {
  name: 'thirteen',
  displayName: 'Thirteen',
  description:
    'The Vietnamese climbing game Tiến lên: race to shed all 13 cards by beating the pile with a higher single, pair, triple, straight — or a bomb.',
  shortDescription:
    'Shed all 13 cards first — beat the pile with a higher combo, or pass.',
  thumbnail: 'games/thirteen.png',
  featured: true,
  order: 7,
  Feedback: ThirteenFeedback,
  ResultsDisplay: ThirteenResultsDisplay,
  // Consumed by /GamePreview/:gameName for backend-free UI development
  sampleFeedback,
};
