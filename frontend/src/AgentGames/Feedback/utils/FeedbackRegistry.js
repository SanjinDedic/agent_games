import MarkdownFeedback from '../types/MarkdownFeedback';
import JsonFeedback from '../types/JsonFeedback';
import PrisonersFeedback from '../games/prisoners_dilemma/PrisonersFeedback';
import Connect4Feedback from '../games/connect4/Connect4Feedback';

export const getFeedbackComponent = (feedback) => {
    // Handle game-specific feedback
    if (typeof feedback === 'object' && feedback?.game) {
        switch (feedback.game) {
            case 'prisoners_dilemma':
                return PrisonersFeedback;
            case 'connect4':
                return Connect4Feedback;
            default:
                return JsonFeedback;
        }
    }

    // Handle generic feedback types
    if (typeof feedback === 'string') {
        return MarkdownFeedback;
    }

    if (typeof feedback === 'object' && feedback !== null && !Array.isArray(feedback)) {
        return JsonFeedback;
    }

    return () => (
        <div className="text-danger font-medium">
            Error: Unsupported feedback format
        </div>
    );
};