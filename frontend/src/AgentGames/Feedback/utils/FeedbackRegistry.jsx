import MarkdownFeedback from '../types/MarkdownFeedback';
import JsonFeedback from '../types/JsonFeedback';
import { getGame } from '../games';

export const getFeedbackComponent = (feedback) => {
    if (typeof feedback === 'object' && feedback?.game) {
        const game = getGame(feedback.game);
        if (game?.Feedback) return game.Feedback;
        return JsonFeedback;
    }

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
