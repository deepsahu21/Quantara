-- drop the old tables if they exist already
DROP TABLE IF EXISTS merged_data;
DROP TABLE IF EXISTS stocks;
DROP TABLE IF EXISTS daily_sentiment;

-- create stocks tabls

CREATE TABLE IF NOT EXISTS stocks (

	date DATE NOT NULL,
	ticker VARCHAR(10) NOT NULL,
	open_price NUMERIC(10,2),
	high_price NUMERIC(10,2),
	low_price NUMERIC(10,2),
	close_price NUMERIC(10,2),
	volume BIGINT,
	PRIMARY KEY(date, ticker)
);

--Create daily sentiment scores table
CREATE TABLE IF NOT EXISTS daily_sentiment (

	date DATE NOT NULL,
	ticker VARCHAR(10) NOT NULL,
	sentiment_score NUMERIC(12,10),
    polarity NUMERIC(6,5),
    headline_count INT,
	PRIMARY KEY(date, ticker)
);

-- load the stock data
\COPY stocks (date, ticker, open_price, high_price, low_price, close_price, volume) FROM 'C:/Users/deeps/Desktop/projects/Quantara/backend/data/processed_data/all_stocks_long.csv' DELIMITER ',' CSV HEADER;

-- load the sentiment data
\COPY daily_sentiment (date, ticker, sentiment_score, polarity, headline_count) FROM 'C:/Users/deeps/Desktop/projects/Quantara/backend/data/processed_data/daily_sentiment.csv' DELIMITER ',' CSV HEADER;



-- Create the merged data table

CREATE TABLE IF NOT EXISTS merged_data (

	ticker VARCHAR(10) NOT NULL,
	date DATE NOT NULL,
	open_price NUMERIC(10,2),
	high_price NUMERIC(10,2),
	low_price NUMERIC(10,2),
	close_price NUMERIC(10,2),
	volume BIGINT,
	sentiment_score NUMERIC(12,10),
    polarity NUMERIC(6,5),
    headline_count INT,
	PRIMARY KEY(date, ticker)
);

-- Insert data into merged table
INSERT INTO merged_data (ticker, date, open_price, high_price, low_price,  close_price, volume, sentiment_score, polarity, headline_count)
    SELECT
        s.ticker,
        s.date,
        s.open_price,
        s.high_price,
        s.low_price,
        s.close_price,
        s.volume,
        d.sentiment_score,
        d.polarity,
        d.headline_count
    FROM stocks s
    JOIN daily_sentiment d
        ON s.date = d.date AND s.ticker = d.ticker;

COPY merged_data TO 'C:/Users/deeps/Desktop/projects/Quantara/backend/data/processed_data/merged_data.csv'
DELIMITER ','
CSV HEADER;