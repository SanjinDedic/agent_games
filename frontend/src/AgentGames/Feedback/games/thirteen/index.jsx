import ThirteenFeedback from './ThirteenFeedback';
import ThirteenResultsDisplay from './ThirteenResultsDisplay';
import sampleFeedback from './sample_feedback.json';
import sampleResults from './sample_results.json';

export default {
  name: 'thirteen',
  displayName: 'Thirteen',
  description:
    'The Vietnamese climbing game Tiến lên: a four-player shedding race to empty your hand. Beat the pile with a higher combo of the same shape — single, pair, triple, straight or a four-of-a-kind bomb — or pass. Hoard your 2s and your bomb for tempo; the order you finish is your placement.',
  shortDescription:
    'Shed all 13 cards first — beat the pile with a higher combo, or pass.',
  thumbnail: 'games/thirteen.png',
  featured: false,
  order: 7,
  Feedback: ThirteenFeedback,
  ResultsDisplay: ThirteenResultsDisplay,
  // Consumed by /GamePreview/:gameName for backend-free UI development
  sampleFeedback,
  sampleResults,
};
