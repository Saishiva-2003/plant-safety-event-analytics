// Loading / error wrappers so every page handles slow or failed API calls the same way.
export function Loader({ text = "Loading..." }) {
  return <div className="loader">{text}</div>;
}

export function ErrorBox({ message, onRetry }) {
  return (
    <div className="error-box">
      <b>Could not load data.</b> {message}{" "}
      {onRetry && (
        <button className="secondary" style={{ marginLeft: 8 }} onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

// Renders loader / error / children depending on a useFetch() result
export function Async({ state, children }) {
  if (state.loading && !state.data) return <Loader />;
  if (state.error) return <ErrorBox message={state.error} onRetry={state.reload} />;
  if (!state.data) return null;
  return children(state.data);
}