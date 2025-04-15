import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import ResultsDisplay from './Shared/Utilities/ResultsDisplay';
import FeedbackSelector from './Feedback/FeedbackSelector';

const PublishedResults = () => {
  const { publishLink } = useParams();
  const [isLoading, setIsLoading] = useState(true);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  // Use the environment API URL
  const apiUrl = process.env.REACT_APP_AGENT_API_URL;

  useEffect(() => {
    if (!publishLink) {
      setError("No publish link provided");
      setIsLoading(false);
      return;
    }

    const fetchResults = async () => {
      try {
        const response = await fetch(`${apiUrl}/user/published-result/${publishLink}`);
        const data = await response.json();

        if (data.status === "success" && data.data) {
          // Make sure to include the game property in feedback if not present
          if (data.data.feedback && !data.data.feedback.game && data.data.game) {
            // If feedback doesn't have game property but results do, add it
            if (typeof data.data.feedback === 'object') {
              data.data.feedback.game = data.data.game;
            } else {
              // If feedback is a string, convert it to an object with game
              data.data.feedback = {
                message: data.data.feedback,
                game: data.data.game
              };
            }
          }
          
          setResults(data.data);
          document.title = `Results for ${data.data.league_name}`;
        } else {
          setError(data.message || "Failed to load results");
          toast.error(data.message || "Failed to load results");
        }
      } catch (error) {
        console.error("Error fetching published results:", error);
        setError("Error connecting to server");
        toast.error("Error connecting to server");
      } finally {
        setIsLoading(false);
      }
    };

    fetchResults();
  }, [publishLink, apiUrl]);

  return (
    <div className="min-h-screen bg-ui-lighter">
      <header className="bg-league-blue shadow-md p-4">
        <div className="container mx-auto flex justify-between items-center">
          <h1 className="text-2xl font-bold text-white">Published Results</h1>
          <Link to="/" className="text-white hover:text-league-text">
            Return to Home
          </Link>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
          </div>
        ) : error ? (
          <div className="bg-danger-light text-danger p-6 rounded-lg text-center">
            <h2 className="text-xl font-bold mb-2">Error</h2>
            <p>{error}</p>
            <p className="mt-4">
              This link may be invalid or the results may have been removed.
            </p>
          </div>
        ) : results ? (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold text-ui-dark mb-4">
              Results for {results.league_name}
            </h2>
            <div className="mb-4 text-ui">
              <p>
                Published on:{" "}
                {new Date(results.timestamp).toLocaleString()}
              </p>
              <p>Number of simulations: {results.num_simulations}</p>
              <p>Game type: {results.game}</p>
            </div>

            <ResultsDisplay
              data={results}
              highlight={false}
              tablevisible={true}
            />

            {results.feedback && (
              <div className="mt-6">
                <h3 className="text-xl font-semibold text-ui-dark mb-2">
                  Feedback
                </h3>
                <FeedbackSelector feedback={results.feedback} startExpanded={true} />
              </div>
            )}
            
            <div className="mt-8 pt-4 border-t border-ui-light">
              <div className="flex justify-between items-center">
                <span className="text-ui-dark">League: {results.league_name}</span>
                <Link to="/" className="text-primary hover:text-primary-hover">
                  Return to Home
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center">No results found</div>
        )}
      </main>
    </div>
  );
};

export default PublishedResults;