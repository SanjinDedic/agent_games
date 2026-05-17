import PrisonersFeedback from './PrisonersFeedback';

export default {
  name: 'prisoners_dilemma',
  displayName: "Prisoner's Dilemma",
  description:
    'Classic game theory scenario where players must choose to cooperate or defect, balancing individual vs. collective benefit.',
  shortDescription:
    'The classic cooperation vs. betrayal game theory problem.',
  thumbnail: 'games/prisoners_dilemma.png',
  featured: true,
  order: 2,
  Feedback: PrisonersFeedback,
  ResultsDisplay: null,
};
