import streamlit as st
import pandas as pd
import json
import plotly.express as px
import os
from PIL import Image
import random
import folium
from streamlit_folium import st_folium
import base64

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# Load translations
@st.cache_data
def load_translations():
    """Load translations from JSON file"""
    translations_path = os.path.join(SCRIPT_DIR, 'translations.json')
    try:
        with open(translations_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("❌ translations.json file not found!")
        return {"en": {}, "ja": {}}
    except Exception as e:
        st.error(f"❌ Error loading translations: {e}")
        return {"en": {}, "ja": {}}


def get_text(key, lang="en", **kwargs):
    """Get translated text with optional formatting"""
    translations = load_translations()
    try:
        text = translations[lang][key]
        if kwargs:
            return text.format(**kwargs)
        return text
    except KeyError:
        # Fallback to English if translation not found
        try:
            text = translations["en"][key]
            if kwargs:
                return text.format(**kwargs)
            return text
        except KeyError:
            return f"[Missing: {key}]"


# Initialize language in session state
if 'language' not in st.session_state:
    st.session_state.language = 'en'

# Set page config
st.set_page_config(
    page_title=get_text("page_title", st.session_state.language),
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-top: -1rem !important;
        margin-bottom: 0.5rem !important;
        font-weight: bold;
        padding-top: 0rem !important;
    }

    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }

    .element-container {
        margin-bottom: 0.2rem !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #28a745 !important;
    }

    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #90EE90 !important;
    }

    .stTabs [data-baseweb="tab-list"] button {
        color: #FFFFFF !important;
    }

    div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
        background-color: #28a745 !important;
        border-color: #28a745 !important;
    }

    .language-toggle {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 999;
    }
</style>
""", unsafe_allow_html=True)

# Photo folder path
PHOTO_FOLDER = os.path.join(SCRIPT_DIR, 'matsuri_pb_photo')


@st.cache_data
def load_blog_data():
    """Load and process blog data from JSON file"""
    try:
        blog_data_path = os.path.join(SCRIPT_DIR, 'blog_data_scrape.json')
        with open(blog_data_path, 'r', encoding='utf-8') as f:
            blog_data = json.load(f)

        df = pd.DataFrame(blog_data)
        df['datetime'] = pd.to_datetime(df['date'], format='%Y/%m/%d', errors='coerce')
        df = df.dropna(subset=['datetime'])

        df['year'] = df['datetime'].dt.year
        df['month'] = df['datetime'].dt.month
        df['day'] = df['datetime'].dt.day
        df['weekday'] = df['datetime'].dt.day_name()
        df['month_name'] = df['datetime'].dt.month_name()
        df['date_only'] = df['datetime'].dt.date

        return df
    except Exception as e:
        st.error(get_text("error_loading_data", st.session_state.language, error=str(e)))
        return None


@st.cache_data
def load_locations():
    """Load locations data for map"""
    locations_path = os.path.join(SCRIPT_DIR, 'locations.json')
    with open(locations_path, 'r') as f:
        return json.load(f)


def image_to_base64(img_path):
    """Convert image to base64 string"""
    with open(img_path, 'rb') as img_file:
        return base64.b64encode(img_file.read()).decode()


def create_daily_timeline(df):
    """Create daily timeline chart"""
    daily_counts = df.groupby('date_only').size().reset_index(name='post_count')
    daily_counts['date_only'] = pd.to_datetime(daily_counts['date_only'])

    date_range = pd.date_range(
        start=daily_counts['date_only'].min(),
        end=daily_counts['date_only'].max(),
        freq='D'
    )

    complete_timeline = pd.DataFrame({'date_only': date_range})
    complete_timeline = complete_timeline.merge(daily_counts, on='date_only', how='left')
    complete_timeline['post_count'] = complete_timeline['post_count'].fillna(0)

    return complete_timeline


def create_timeline_chart(timeline_df, lang):
    """Create interactive timeline chart"""
    fig = px.bar(
        timeline_df,
        x='date_only',
        y='post_count',
        title=get_text("timeline_title", lang),
        labels={
            'date_only': get_text("timeline_x_label", lang),
            'post_count': get_text("timeline_y_label", lang)
        },
        color_discrete_sequence=['#E0E26A']
    )

    fig.update_layout(
        font=dict(family="Arial, sans-serif", size=12, color="black"),
        title_font_size=20,
        height=320,
        showlegend=False,
        hovermode='x unified',
        xaxis=dict(
            title=get_text("timeline_x_label", lang),
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(0,0,0,0)'
        ),
        yaxis=dict(
            title=get_text("timeline_y_label", lang),
            showgrid=True,
            gridwidth=1,
            dtick=1,
        ),
    )

    fig.update_traces(
        hovertemplate=f"<b>{get_text('timeline_hover_date', lang)}</b> %{{x}}<br><b>{get_text('timeline_hover_posts', lang)}</b> %{{y}}<extra></extra>"
    )

    return fig


def create_monthly_summary(df, lang):
    """Create monthly summary chart"""
    monthly_counts = df.groupby(['year', 'month_name']).size().reset_index(name='post_count')

    month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']

    monthly_counts['month_name'] = pd.Categorical(monthly_counts['month_name'],
                                                  categories=month_order,
                                                  ordered=True)

    monthly_counts = monthly_counts.sort_values(['year', 'month_name'])
    monthly_counts['year_month'] = monthly_counts['year'].astype(str) + ' ' + monthly_counts['month_name'].astype(str)

    fig = px.bar(
        monthly_counts,
        x='year_month',
        y='post_count',
        title=get_text("monthly_title", lang),
        labels={
            'year_month': get_text("monthly_x_label", lang),
            'post_count': get_text("monthly_y_label", lang)
        },
        color='post_count',
        color_continuous_scale=[[0, '#013220'], [0.5, '#7CB342'], [1, '#FFF176']]
    )

    fig.update_xaxes(
        categoryorder='array',
        categoryarray=monthly_counts['year_month'].tolist(),
        tickangle=-45
    )

    fig.update_layout(height=350)
    return fig


def create_weekday_analysis(df, lang):
    """Create weekday analysis chart"""
    weekday_counts = df['weekday'].value_counts()
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekday_counts = weekday_counts.reindex([day for day in weekday_order if day in weekday_counts.index])

    fig = px.bar(
        x=weekday_counts.index,
        y=weekday_counts.values,
        title=get_text("weekday_title", lang),
        labels={
            'x': get_text("weekday_x_label", lang),
            'y': get_text("weekday_y_label", lang)
        },
        color=weekday_counts.values,
        color_continuous_scale=[[0, '#013220'], [0.5, '#7CB342'], [1, '#FFF176']]
    )

    fig.update_layout(height=320)
    return fig


def main():
    # Header with language toggle button in same line
    col1, col2, col3 = st.columns([1, 6, 1])

    with col2:
        st.markdown(f'<h1 class="main-header">{get_text("main_header", st.session_state.language)}</h1>',
                    unsafe_allow_html=True)

    with col3:
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)  # Align with header
        if st.button(get_text("language_toggle", st.session_state.language)):
            st.session_state.language = 'ja' if st.session_state.language == 'en' else 'en'
            st.rerun()

    # Load data
    df = load_blog_data()

    if df is None or df.empty:
        st.error(get_text("error_no_data", st.session_state.language))
        st.info(get_text("info_json_structure", st.session_state.language))
        return

    df_filtered = df

    if df_filtered.empty:
        st.warning(get_text("warning_no_data", st.session_state.language))
        return

    timeline_df = create_daily_timeline(df_filtered)

    # Tabs with translations - Added tab_map before tab_disclaimer
    tab1, tab2, tab3, tab5, tab7, tab_map, tab8 = st.tabs([
        get_text("tab_timeline", st.session_state.language),
        get_text("tab_monthly", st.session_state.language),
        get_text("tab_weekday", st.session_state.language),
        get_text("tab_total", st.session_state.language),
        get_text("tab_photo", st.session_state.language),
        "🗺️ PHOTOBOOK MAP SP",  # New Map tab before disclaimer
        get_text("tab_disclaimer", st.session_state.language)
    ])

    with tab1:
        timeline_fig = create_timeline_chart(timeline_df, st.session_state.language)
        st.plotly_chart(timeline_fig, use_container_width=True)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label=get_text("metric_total_posts", st.session_state.language),
                value=len(df_filtered)
            )

        with col3:
            avg_posts = len(df_filtered) / df_filtered['date_only'].nunique()
            st.metric(
                label=get_text("metric_avg_posts", st.session_state.language),
                value=f"{avg_posts:.1f}"
            )

        with col4:
            max_posts = df_filtered.groupby('date_only').size().max()
            st.metric(
                label=get_text("metric_max_posts", st.session_state.language),
                value=max_posts
            )

        col1, col2 = st.columns(2)
        with col2:
            st.subheader(get_text("top_active_days", st.session_state.language))
            top_days = timeline_df.nlargest(10, 'post_count')[['date_only', 'post_count']]
            top_days['date_only'] = top_days['date_only'].dt.strftime('%Y-%m-%d')
            top_days.columns = [
                get_text("column_date", st.session_state.language),
                get_text("column_posts", st.session_state.language)
            ]
            st.dataframe(top_days, hide_index=True)

    with tab2:
        monthly_fig = create_monthly_summary(df_filtered, st.session_state.language)
        st.plotly_chart(monthly_fig, use_container_width=True)

        monthly_stats = df_filtered.groupby(['year', 'month_name']).size().reset_index(name='post_count')
        monthly_stats['year_month'] = monthly_stats['year'].astype(str) + ' ' + monthly_stats['month_name']
        monthly_stats = monthly_stats[['year_month', 'post_count']].sort_values('post_count', ascending=False)
        monthly_stats.columns = [
            get_text("column_month", st.session_state.language),
            get_text("column_posts", st.session_state.language)
        ]
        st.dataframe(monthly_stats, hide_index=True)

    with tab3:
        weekday_fig = create_weekday_analysis(df_filtered, st.session_state.language)
        st.plotly_chart(weekday_fig, use_container_width=True)

        weekday_stats = df_filtered['weekday'].value_counts()
        weekday_df = pd.DataFrame({
            get_text("column_day", st.session_state.language): weekday_stats.index,
            get_text("column_posts", st.session_state.language): weekday_stats.values,
            get_text("column_percentage", st.session_state.language): (
                        weekday_stats.values / len(df_filtered) * 100).round(1)
        })
        st.dataframe(weekday_df, hide_index=True)

    with tab5:
        try:
            counts_path = os.path.join(SCRIPT_DIR, "blog_data_counts.json")
            with open(counts_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                st.error(get_text("error_json_list", st.session_state.language))
                st.json(data[:2])
            else:
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(get_text("metric_total_blogs", st.session_state.language), data.get("total_blogs", "N/A"))

                with col2:
                    st.metric(get_text("metric_total_chars", st.session_state.language),
                              f"{data.get('total_characters', 0):,}")

                with col3:
                    st.metric(get_text("metric_total_images", st.session_state.language),
                              f"{data.get('total_images', 0):,}")

                col5, col6 = st.columns(2)
                with col5:
                    avg_chars = data.get('average_characters', 0)
                    st.metric(get_text("metric_avg_chars", st.session_state.language), f"{avg_chars:.1f}")
                with col6:
                    avg_images = data.get('average_images', 0)
                    st.metric(get_text("metric_avg_images", st.session_state.language), f"{avg_images:.1f}")

        except FileNotFoundError:
            st.error(get_text("error_json_not_found", st.session_state.language))
        except Exception as e:
            st.error(get_text("error_loading_data", st.session_state.language, error=str(e)))
            st.write(get_text("debug_info", st.session_state.language))

    with tab7:
        display_mode = "Grid View"
        photo_folder = os.path.join(SCRIPT_DIR, "matsuri_blog_photo")

        try:
            if not os.path.exists(photo_folder):
                st.error(get_text("error_directory_not_found", st.session_state.language, folder=photo_folder))
                st.info(get_text("info_supported_formats", st.session_state.language))
                return

            supported_formats = ('.jpg')
            image_files = []

            for file in os.listdir(photo_folder):
                if file.lower().endswith(supported_formats):
                    image_files.append(os.path.join(photo_folder, file))

            if not image_files:
                st.warning(get_text("error_no_images", st.session_state.language, folder=photo_folder))
                st.info(get_text("info_add_photos", st.session_state.language))
                return

            col1, col2 = st.columns(2)
            with col1:
                if st.button(get_text("button_shuffle", st.session_state.language)):
                    if 'shuffled_images' not in st.session_state:
                        st.session_state.shuffled_images = image_files.copy()
                    random.shuffle(st.session_state.shuffled_images)
                    st.rerun()

            display_images = st.session_state.get('shuffled_images', image_files)
            display_images = display_images[:20]

            if display_mode == "Grid View":
                cols = st.columns(5)
                for idx, image_path in enumerate(display_images):
                    with cols[idx % 5]:
                        try:
                            image = Image.open(image_path)
                            st.image(image, use_container_width=True)
                        except Exception as e:
                            st.error(get_text("error_loading_image", st.session_state.language, path=image_path,
                                              error=str(e)))

        except Exception as e:
            st.error(get_text("error_unexpected", st.session_state.language, error=str(e)))

    # ===== NEW MAP TAB (before disclaimer) =====
    with tab_map:
        # Google Maps link button
        col1, col3 = st.columns([4, 2])

        with col1:
            col_title, col_button = st.columns([3, 1])
            with col_title:
                st.subheader("Location map for the 1st Photobook")
            with col_button:
                st.markdown("<div style='margin-top: 0.1rem;'></div>", unsafe_allow_html=True)
                if st.link_button("🔗 Google Maps", "https://maps.app.goo.gl/tQ45ZPTU6xyDZM8a6"):
                    pass

            data = load_locations()

            avg_lat = sum(loc['lat'] for loc in data['locations']) / len(data['locations'])
            avg_lon = sum(loc['lon'] for loc in data['locations']) / len(data['locations'])

            m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)

            for location in data['locations']:
                # Create popup HTML with embedded image
                popup_html = f"""
                <div style="width: 300px;">
                    <h4 style="margin-bottom: 10px;">{location['name']}</h4>
                    <p style="margin-bottom: 10px;">{location['description']}</p>
                """

                # Add images to popup
                if 'images' in location and location['images']:
                    for img_filename in location['images'][:1]:
                        img_path = os.path.join(PHOTO_FOLDER, img_filename)
                        if os.path.exists(img_path):
                            img_base64 = image_to_base64(img_path)
                            popup_html += f"""
                            <img src="data:image/jpeg;base64,{img_base64}" 
                                 style="width: 100%; margin-bottom: 5px; border-radius: 5px;">
                            """

                popup_html += "</div>"

                # Create tooltip with image
                tooltip_html = f"""
                <div style="width: 250px; font-family: Arial, sans-serif;">
                """

                # Add second image to tooltip if available
                if 'images' in location and location['images']:
                    img_path = os.path.join(PHOTO_FOLDER, location['images'][1])
                    if os.path.exists(img_path):
                        img_base64 = image_to_base64(img_path)
                        tooltip_html += f"""
                        <img src="data:image/jpeg;base64,{img_base64}" 
                             style="width: 100%; height: 100%; object-fit: cover; border-radius: 8px; margin-bottom: 8px;">
                        """

                # Create popup with custom size
                popup = folium.Popup(popup_html, max_width=320)

                folium.Marker(
                    [location['lat'], location['lon']],
                    popup=popup,
                    tooltip=folium.Tooltip(tooltip_html),
                    icon=folium.Icon(color=location['color'], icon=location['icon'])
                ).add_to(m)

            map_data = st_folium(m, width=None, height=700, key="map")

        # Find clicked location
        clicked_location = None
        if map_data and map_data.get('last_object_clicked'):
            clicked_lat = map_data['last_object_clicked']['lat']
            clicked_lon = map_data['last_object_clicked']['lng']

            # Find matching location (with small tolerance for floating point comparison)
            for location in data['locations']:
                if abs(location['lat'] - clicked_lat) < 0.0001 and abs(location['lon'] - clicked_lon) < 0.0001:
                    clicked_location = location
                    break

        with col3:
            st.subheader("📸 Photos")

            if clicked_location:
                st.markdown(f"**{clicked_location['name']}**")

                if 'images' in clicked_location and clicked_location['images']:
                    for j, img_filename in enumerate(clicked_location['images'], 1):
                        img_path = os.path.join(PHOTO_FOLDER, img_filename)

                        if os.path.exists(img_path):
                            st.image(img_path, caption=f"Photo {j}", use_container_width=True)
                        else:
                            st.warning(f"Image not found: {img_filename}")
                else:
                    st.info("No images available for this location")
            else:
                st.info("👆 Click on a marker to see photos")
    # ===== END MAP TAB =====

    with tab8:
        st.write(get_text("disclaimer_main", st.session_state.language))
        st.write(get_text("disclaimer_data", st.session_state.language))
        st.write(get_text("disclaimer_official", st.session_state.language))
        st.write(get_text("disclaimer_copyright", st.session_state.language))

    # Footer
    min_date = df['datetime'].min().date()
    max_date = df['datetime'].max().date()
    st.markdown("---")
    st.markdown(
        f"{get_text('footer_dashboard', st.session_state.language)} | "
        f"{get_text('footer_data_range', st.session_state.language, min_date=min_date, max_date=max_date)} "
        f"| {get_text('footer_made_with', st.session_state.language)}"
    )


if __name__ == "__main__":
    main()

# Happy birthday, Captain Matsuri!
