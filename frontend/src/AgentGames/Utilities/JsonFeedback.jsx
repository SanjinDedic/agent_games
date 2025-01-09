import React from 'react';
import JSONPretty from 'react-json-pretty';
import 'react-json-pretty/themes/monikai.css';

const JsonFeedback = ({ feedback }) => {
  const renderContent = () => {
    if (typeof feedback !== 'object' || feedback === null || Array.isArray(feedback)) {
      return <div className="text-danger font-medium">Error: JSON feedback must be an object</div>;
    }

    return (
      <JSONPretty
        id="json-pretty"
        data={feedback}
        className="p-4 text-left"
      />
    );
  };

  return (
    <div className="mt-4">
      {renderContent()}
    </div>
  );
};

export default JsonFeedback;