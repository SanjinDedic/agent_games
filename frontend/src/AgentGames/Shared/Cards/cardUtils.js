// Shared helpers for card games. Cards are compact codes: rank + suit letter,
// e.g. "QS", "10H", "2C". Suit is always the last character.

export const RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'];

export const SUIT_ORDER = ['C', 'D', 'S', 'H'];

export const SUITS = {
    C: { symbol: '♣', name: 'Clubs', color: 'text-ui-dark' },
    D: { symbol: '♦', name: 'Diamonds', color: 'text-danger' },
    S: { symbol: '♠', name: 'Spades', color: 'text-ui-dark' },
    H: { symbol: '♥', name: 'Hearts', color: 'text-danger' },
};

export const parseCard = (code) => {
    const suit = code.slice(-1);
    const rank = code.slice(0, -1);
    return {
        code,
        rank,
        suit,
        value: RANKS.indexOf(rank) + 2,
        ...SUITS[suit],
    };
};

// Sort for display: clubs, diamonds, spades, hearts — low to high within suit
export const sortCards = (codes) =>
    [...codes].sort((a, b) => {
        const ca = parseCard(a);
        const cb = parseCard(b);
        if (ca.suit !== cb.suit) {
            return SUIT_ORDER.indexOf(ca.suit) - SUIT_ORDER.indexOf(cb.suit);
        }
        return ca.value - cb.value;
    });
