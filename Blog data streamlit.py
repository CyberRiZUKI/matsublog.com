import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import calendar
from collections import Counter

# Set page config
st.set_page_config(
    page_title="Blog Posts Timeline Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_blog_data(uploaded_file):
    """Load and process blog data from JSON file"""
    try:
        if uploaded_file is not None:
            blog_data = json.load(uploaded_file)
        else:
            # Try to load from default file
            with open('blog_data_scrape.json', 'r', encoding='utf-8') as f:
                blog_data = json.load(f)

        # Convert to DataFrame
        df = pd.DataFrame(blog_data)

        # Parse dates
        df['datetime'] = pd.to_datetime(df['date'], format='%Y/%m/%d', errors='coerce')
        df = df.dropna(subset=['datetime'])  # Remove rows with invalid dates

        # Extract date components
        df['year'] = df['datetime'].dt.year
        df['month'] = df['datetime'].dt.month
        df['day'] = df['datetime'].dt.day
        df['weekday'] = df['datetime'].dt.day_name()
        df['month_name'] = df['datetime'].dt.month_name()
        df['date_only'] = df['datetime'].dt.date

        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None


def create_daily_timeline(df):
    """Create daily timeline chart"""
    # Group by date and count posts
    daily_counts = df.groupby('date_only').size().reset_index(name='post_count')
    daily_counts['date_only'] = pd.to_datetime(daily_counts['date_only'])

    # Create a complete date range to show days with 0 posts
    date_range = pd.date_range(
        start=daily_counts['date_only'].min(),
        end=daily_counts['date_only'].max(),
        freq='D'
    )

    complete_timeline = pd.DataFrame({'date_only': date_range})
    complete_timeline = complete_timeline.merge(daily_counts, on='date_only', how='left')
    complete_timeline['post_count'] = complete_timeline['post_count'].fillna(0)

    return complete_timeline


def create_timeline_chart(timeline_df):
    """Create interactive timeline chart - always bar chart"""
    fig = px.bar(
        timeline_df,
        x='date_only',
        y='post_count',
        title="📊 Daily Blog Posts Timeline (Bar Chart)",
        labels={'date_only': 'Date', 'post_count': 'Number of Posts'}
    )

    # Apply black font to all text elements
    fig.update_layout(
        font=dict(
            family="Arial, sans-serif",
            size=12,
            color="black"  # This sets ALL text to black
        ),
        title_font_size=20,
        height=500,
        showlegend=False,
        hovermode='x unified',
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(0,0,0,0)'
        ),
        yaxis=dict(
            title="Number of Posts",
            showgrid=True,
            gridwidth=1,
            dtick=1,  # Added: Force integer ticks
        ),
    )

    # Add hover template
    fig.update_traces(
        hovertemplate="<b>Date:</b> %{x}<br><b>Posts:</b> %{y}<extra></extra>"
    )

    return fig


def create_monthly_summary(df):
    """Create monthly summary chart"""
    monthly_counts = df.groupby(['year', 'month_name']).size().reset_index(name='post_count')

    # Create a proper month order for sorting
    month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']

    # Convert month_name to categorical with proper order
    monthly_counts['month_name'] = pd.Categorical(monthly_counts['month_name'],
                                                  categories=month_order,
                                                  ordered=True)

    # Sort by year and month chronologically
    monthly_counts = monthly_counts.sort_values(['year', 'month_name'])

    # Create year_month for display AFTER sorting
    monthly_counts['year_month'] = monthly_counts['year'].astype(str) + ' ' + monthly_counts['month_name'].astype(str)

    fig = px.bar(
        monthly_counts,
        x='year_month',
        y='post_count',
        title="📅 Monthly Blog Posts Summary",
        labels={'year_month': 'Month', 'post_count': 'Number of Posts'},
        color='post_count',
        color_continuous_scale=[[0, '#013220'], [0.5, '#7CB342'], [1, '#FFF176']]  # Very dark green → Light green → Light yellow

    )

    # Use update_xaxes() instead of update_xaxis()
    fig.update_xaxes(
        categoryorder='array',
        categoryarray=monthly_counts['year_month'].tolist(),
        tickangle=-45
    )

    fig.update_layout(
        height=400
    )

    return fig


def create_weekday_analysis(df):
    """Create weekday analysis chart"""
    weekday_counts = df['weekday'].value_counts()
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekday_counts = weekday_counts.reindex([day for day in weekday_order if day in weekday_counts.index])

    fig = px.bar(
        x=weekday_counts.index,
        y=weekday_counts.values,
        title="📊 Posts by Day of Week",
        labels={'x': 'Day of Week', 'y': 'Number of Posts'},
        color=weekday_counts.values,
        color_continuous_scale=[[0, '#013220'], [0.5, '#7CB342'], [1, '#FFF176']]
    )

    fig.update_layout(height=400)

    return fig


def main():
    # Header
    st.markdown('<h1 class="main-header">📊 熱烈祝賀隊長松田里奈擔任宮崎大使為推廣家鄉出一份力</h1>', unsafe_allow_html=True)

    # Sidebar
    st.sidebar.title("🎛️ Dashboard Controls")

    # File upload
    uploaded_file = st.sidebar.file_uploader(
        "Upload JSON file",
        type=['json'],
        help="Upload your blog_data.json file"
    )

    # Load data
    df = load_blog_data(uploaded_file)

    if df is None or df.empty:
        st.error(
            "❌ No data loaded. Please upload a valid JSON file or ensure 'blog_data.json' exists in the current directory.")
        st.info("💡 The JSON file should contain blog data with 'date', 'title', and 'page' fields.")
        return

    # Use the full dataset (no filtering)
    df_filtered = df

    # Main dashboard
    if df_filtered.empty:
        st.warning("⚠️ No data available.")
        return

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📚 Total Posts",
            value=len(df_filtered)
        )

    with col2:
        st.metric(
            label="📅 Active Days",
            value=df_filtered['date_only'].nunique()
        )

    with col3:
        avg_posts = len(df_filtered) / df_filtered['date_only'].nunique()
        st.metric(
            label="📊 Avg Posts/Day",
            value=f"{avg_posts:.1f}"
        )

    with col4:
        max_posts = df_filtered.groupby('date_only').size().max()
        st.metric(
            label="🔥 Max Posts/Day",
            value=max_posts
        )

    # Create timeline
    timeline_df = create_daily_timeline(df_filtered)

    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5= st.tabs([
        "📈 Timeline", "📊 Monthly Summary",
        "🗓️ Weekday Analysis", "📋 Data Table", "📋Total data"
    ])

    with tab1:
        st.subheader("Daily Posts Timeline")

        # Timeline chart (always bar chart)
        timeline_fig = create_timeline_chart(timeline_df)
        st.plotly_chart(timeline_fig, use_container_width=True)

        # Additional timeline statistics
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 Timeline Statistics")
            zero_days = (timeline_df['post_count'] == 0).sum()
            active_days = (timeline_df['post_count'] > 0).sum()
            max_day = timeline_df.loc[timeline_df['post_count'].idxmax(), 'date_only'].strftime('%Y-%m-%d')

            st.write(f"**Days with posts:** {active_days}")
            st.write(f"**Days without posts:** {zero_days}")
            st.write(f"**Most active day:** {max_day}")
            st.write(f"**Posts on most active day:** {timeline_df['post_count'].max()}")

        with col2:
            st.subheader("🔥 Top 10 Most Active Days")
            top_days = timeline_df.nlargest(10, 'post_count')[['date_only', 'post_count']]
            top_days['date_only'] = top_days['date_only'].dt.strftime('%Y-%m-%d')
            top_days.columns = ['Date', 'Posts']
            st.dataframe(top_days, hide_index=True)

    with tab2:
        st.subheader("Monthly Summary")
        monthly_fig = create_monthly_summary(df_filtered)
        st.plotly_chart(monthly_fig, use_container_width=True)

        # Monthly statistics table
        monthly_stats = df_filtered.groupby(['year', 'month_name']).size().reset_index(name='post_count')
        monthly_stats['year_month'] = monthly_stats['year'].astype(str) + ' ' + monthly_stats['month_name']
        monthly_stats = monthly_stats[['year_month', 'post_count']].sort_values('post_count', ascending=False)
        monthly_stats.columns = ['Month', 'Posts']

        st.subheader("📊 Monthly Statistics")
        st.dataframe(monthly_stats, hide_index=True)

    with tab3:
        st.subheader("Weekday Analysis")
        weekday_fig = create_weekday_analysis(df_filtered)
        st.plotly_chart(weekday_fig, use_container_width=True)

        # Weekday statistics
        weekday_stats = df_filtered['weekday'].value_counts()
        weekday_df = pd.DataFrame({
            'Day': weekday_stats.index,
            'Posts': weekday_stats.values,
            'Percentage': (weekday_stats.values / len(df_filtered) * 100).round(1)
        })

        st.subheader("📊 Weekday Statistics")
        st.dataframe(weekday_df, hide_index=True)

    with tab4:
        st.subheader("Raw Data")

        # Search functionality
        search_term = st.text_input("🔍 Search in titles:")

        if search_term:
            mask = df_filtered['title'].str.contains(search_term, case=False, na=False)
            display_df = df_filtered[mask]
        else:
            display_df = df_filtered

        # Display options
        col1, col2 = st.columns(2)
        with col1:
            show_columns = st.multiselect(
                "Select columns to display:",
                options=['date', 'title', 'page', 'href', 'weekday', 'month_name'],
                default=['date', 'title', 'page', 'href']
            )

        with col2:
            rows_to_show = st.selectbox(
                "Rows to display:",
                options=[10, 25, 50, 100, len(display_df)],
                index=1
            )

        # Display filtered data
        if show_columns:
            st.dataframe(
                display_df[show_columns].head(rows_to_show),
                hide_index=True,
                use_container_width=True
            )

        # Download button
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download filtered data as CSV",
            data=csv,
            file_name=f"blog_data_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    with tab5:
        st.header("📋 Total data summarize")

        try:
            # Load and display JSON data
            with open("blog_data_counts.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if data is a list instead of dict
            if isinstance(data, list):
                st.error("JSON data is a list, not a dictionary. Please check your JSON structure.")
                st.json(data[:2])  # Show first 2 items
            else:
                # Display summary statistics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("total_blogs", data.get("total_blogs", "N/A"))

                with col2:
                    st.metric("total_characters", f"{data.get('total_characters', 0):,}")

                with col3:
                    st.metric("total_images", f"{data.get('total_images', 0):,}")

                # Display averages
                col5, col6 = st.columns(2)
                with col5:
                    avg_chars = data.get('average_characters', 0)
                    st.metric("Avg Characters/Blog", f"{avg_chars:.1f}")
                with col6:
                    avg_images = data.get('average_images', 0)
                    st.metric("Avg Images/Blog", f"{avg_images:.1f}")

        except FileNotFoundError:
            st.error("❌ blog_data.json file not found. Please run the scraping script first.")
        except Exception as e:
            st.error(f"❌ Error loading data: {e}")
            st.write("Debug info - please check your JSON file structure")

    # Footer
    min_date = df['datetime'].min().date()
    max_date = df['datetime'].max().date()
    st.markdown("---")
    st.markdown(
        "📊 **Blog Timeline Dashboard** | "
        f"Data range: {min_date} to {max_date} | "
        f"Total posts analyzed: {len(df)}"
    )


if __name__ == "__main__":
    main()
