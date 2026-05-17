import ArenaChampionsFeedback from './ArenaChampionsFeedback';
import ArenaChampionsResultsDisplay from './ArenaChampionsResultsDisplay';

export default {
  name: 'arena_champions',
  displayName: 'Arena Champions',
  description:
    'Build a champion that picks stats, attacks, and abilities to outlast rivals across a tournament of arena battles.',
  shortDescription:
    'Pick stats and attacks to outlast rivals across arena battles.',
  thumbnail: 'games/arena_champions.png',
  featured: false,
  order: 4,
  Feedback: ArenaChampionsFeedback,
  ResultsDisplay: ArenaChampionsResultsDisplay,
};
