import OhHellFeedback from './OhHellFeedback';
import OhHellResultsDisplay from './OhHellResultsDisplay';
import sampleFeedback from './sample_feedback.json';
import sampleResults from './sample_results.json';

export default {
  name: 'ohhell',
  displayName: 'Oh Hell!',
  description:
    'The trick-taking game with a twist: win exactly the number of tricks you bid — no more, no fewer. Nail your bid for a fat bonus, miss it and get nothing. Highest score wins.',
  shortDescription:
    'Bid your tricks, then take exactly that many — no more, no fewer.',
  thumbnail: 'games/ohhell.png',
  featured: true,
  order: 6,
  Feedback: OhHellFeedback,
  ResultsDisplay: OhHellResultsDisplay,
  // Consumed by /GamePreview/:gameName for backend-free UI development
  sampleFeedback,
  sampleResults,
};
