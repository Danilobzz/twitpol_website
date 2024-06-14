from google.oauth2 import service_account
from google.cloud import bigquery
import plotly.express as px
import streamlit as st
import pandas as pd
import requests

# Streamlit application title

st.title("Twitpol - Political Sentiment Predictor")

# Function to get tweet prediction

def get_tweet_prediction(tweet):
    try:
        response = requests.get('https://twitpol-ciuj3kmdsa-ew.a.run.app/predict-text',
                                params={'tweet': tweet})

# Raise an exception for non-200 status codes

        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error predicting tweet: {e}")
        return None

# Function to get user predictions

def get_user_prediction(username):
    try:
        response = requests.get('https://twitpol-ciuj3kmdsa-ew.a.run.app/predict-user',
                                params={'username': username})

# Raise an exception for non-200 status codes

        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error predicting user account: {e}")
        return None

# Create API client

secret = st.secrets["gcp_service_account"]
credentials = service_account.Credentials.from_service_account_info(secret)
client = bigquery.Client(credentials=credentials)

# Streamlit input and prediction

option = st.selectbox("Choose input type", ("User", "Text"))
if option == "Text":
    st.header("Predict Sentiment for a Tweet")
    tweet = st.text_area("Enter Tweet:")
    if st.button("Predict Tweet"):
        prediction = get_tweet_prediction(tweet)
        if prediction:
            st.write("Prediction:", prediction)
else:
    st.header("Predict Sentiment for a Twitter Account")
    user = st.text_input("Enter User:")
    if st.button("Predict Account"):
        # Check if user exists in BigQuery
        query = f"""
        SELECT * FROM `twitpol.twitter_account_history.history`
        WHERE name = '{user}'
        """
        query_job = client.query(query)
        results = query_job.result()

        # Convert results to a DataFrame
        df_results = pd.DataFrame([dict(row) for row in results])

        if not df_results.empty:
            # User exists in BigQuery, display the stored results
            st.write("Results:")
            df_results.columns = ["Name", "Neuteral", "Democrats", "Republicans"]


            df_melted = df_results.melt(id_vars=["name"], value_vars=["neu", "dem", "rep"],
                                        var_name="Political Sentiment", value_name="Count")

            most_common_sentiment = df_results[['neu', 'dem', 'rep']].idxmax(axis=1)[0]
            st.write(f"The most common tweet sentiment is: {most_common_sentiment}")

            fig = px.bar(df_melted, x='Political Sentiment', y='Count',
                         labels={'Count': 'Count', 'Political Sentiment': 'Political Sentiment'},
                         title='Political Sentiment Distribution')
            st.plotly_chart(fig)
        else:
            # User does not exist, make API request
            prediction = get_user_prediction(user)
            if prediction:
                df = pd.DataFrame(prediction.items(), columns=['Political Sentiment', 'Count'])
                df.columns = ["Name", "Neuteral", "Democrats", "Republicans"]
                most_common_sentiment = df_results[['Neuteral', 'Democrats', 'Republicans']].idxmax(axis=1)[0]
                st.write(f"The most common tweet sentiment is: {most_common_sentiment}")

                fig = px.bar(df, x='Political Sentiment', y='Count',
                             labels={'Count': 'Count', 'Political Sentiment': 'Political Sentiment'},
                             title='Political Sentiment Distribution')



                st.dataframe(df)
                st.plotly_chart(fig)

                # Prepare DF
                sentiment_counts = {sentiment: count for sentiment, count in prediction.items()}
                sentiment_counts['name'] = user
                sentiment_counts['Neutral'] = df['Count'][0]
                sentiment_counts['Democrat'] = df['Count'][1]
                sentiment_counts['Republican'] = df['Count'][2]

                df_to_save = pd.DataFrame([sentiment_counts], columns=['name', 'neu', 'dem', 'rep'])

                # BigQuery load config
                table_name = "twitpol.twitter_account_history.history"
                job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")

                # Load data to BigQuery
                client.load_table_from_dataframe(dataframe=df_to_save,
                                                 destination=table_name,
                                                 job_config=job_config)

# BigQuery query and display results
#st.header("Results from BigQuery")
#query = "SELECT * FROM `twitpol.twitter_account_history.history` LIMIT 100"
#rows = client.query(query).result()
#df_rows = pd.DataFrame([dict(row) for row in rows])
#df_rows.columns = ["Name", "Neuteral", "Democrats", "Republicans"]
#st.write(df_rows)
