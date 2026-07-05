import HeartsFeedback from './HeartsFeedback';
import HeartsResultsDisplay from './HeartsResultsDisplay';
import sampleFeedback from './sample_feedback.json';

export default {
  name: 'hearts',
  displayName: 'Hearts',
  description:
    'The classic Windows card game. Dodge hearts and the Queen of Spades — or risk it all and shoot the moon. Lowest score wins.',
  shortDescription:
    'Avoid hearts and the Queen of Spades — or shoot the moon.',
  thumbnail: 'games/hearts.png',
  featured: true,
  order: 5,
  Feedback: HeartsFeedback,
  ResultsDisplay: HeartsResultsDisplay,
  // Consumed by /GamePreview/:gameName for backend-free UI development
  sampleFeedback,
};
