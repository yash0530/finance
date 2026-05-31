/**
 * Compact "Research →" action for discovery rows. Clicking sends the ticker
 * straight to Deep Research, bypassing the Stock View detour. Stops event
 * propagation so it can live inside a row whose own click opens Stock View.
 */
export default function ResearchLink({ ticker, onRunResearch, className = '', title }) {
    if (!onRunResearch) return null;
    return (
        <button
            type="button"
            className={`research-link ${className}`}
            title={title || `Run Deep Research on ${ticker}`}
            aria-label={`Run Deep Research on ${ticker}`}
            onClick={(e) => { e.stopPropagation(); onRunResearch(ticker); }}
        >
            R→
        </button>
    );
}
