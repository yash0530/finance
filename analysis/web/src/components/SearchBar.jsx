import { useState, useRef, useEffect } from 'react';
import { searchCompanies, getSectorColor } from '../utils/api';
import './SearchBar.css';

function SearchBar({ onResults }) {
    const [query, setQuery] = useState('');
    const [suggestions, setSuggestions] = useState([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [loading, setLoading] = useState(false);
    const wrapperRef = useRef(null);
    const timeoutRef = useRef(null);

    // Close suggestions when clicking outside
    useEffect(() => {
        function handleClickOutside(event) {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
                setShowSuggestions(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSearch = async (searchQuery) => {
        if (!searchQuery || searchQuery.length < 2) {
            setSuggestions([]);
            setShowSuggestions(false);
            return;
        }

        setLoading(true);
        try {
            const results = await searchCompanies(searchQuery);
            setSuggestions(results.data.slice(0, 8));
            setShowSuggestions(true);
        } catch (err) {
            console.error('Search failed:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleInputChange = (e) => {
        const value = e.target.value;
        setQuery(value);

        // Debounce search
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        timeoutRef.current = setTimeout(() => handleSearch(value), 300);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setShowSuggestions(false);
        try {
            const results = await searchCompanies(query);
            onResults(results);
        } catch (err) {
            console.error('Search failed:', err);
        }
    };

    const handleSelectSuggestion = async (company) => {
        setQuery(company.ticker);
        setShowSuggestions(false);
        onResults({ count: 1, data: [company] });
    };

    return (
        <div className="search-wrapper" ref={wrapperRef}>
            <form onSubmit={handleSubmit} className="search-form">
                <div className="search-input-wrapper">
                    <span className="search-icon">🔍</span>
                    <input
                        type="text"
                        className="search-input"
                        placeholder="Search by ticker or company name..."
                        value={query}
                        onChange={handleInputChange}
                        onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                    />
                    {loading && <span className="search-spinner"></span>}
                </div>
            </form>

            {showSuggestions && suggestions.length > 0 && (
                <div className="suggestions-dropdown">
                    {suggestions.map((company) => (
                        <div
                            key={company.ticker}
                            className="suggestion-item"
                            onClick={() => handleSelectSuggestion(company)}
                        >
                            <span className="suggestion-ticker font-mono">{company.ticker}</span>
                            <span className="suggestion-name">{company.company_name}</span>
                            <span
                                className="suggestion-sector"
                                style={{ color: getSectorColor(company.sector) }}
                            >
                                {company.sector}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default SearchBar;
