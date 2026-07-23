from __future__ import annotations

from pathlib import Path

import streamlit as st

from dashboard.data import assess_data_quality, filter_books, load_books
from exporter.excel import protect_tabular_text

PRIMARY_DATABASE = Path("data/books.sqlite")
SAMPLE_DATABASE = Path("data/sample/books.sqlite")
DEFAULT_DATABASE = (
    PRIMARY_DATABASE if PRIMARY_DATABASE.exists() else SAMPLE_DATABASE
)

st.set_page_config(
    page_title="Catalog Insight",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at 8% 0%, rgba(37, 99, 235, .10), transparent 30%),
            #f7f8fc;
    }
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #e4e8f0;
        border-radius: 18px;
        padding: 1rem;
        box-shadow: 0 10px 30px rgba(15, 23, 42, .05);
    }
    .stMainBlockContainer { padding-top: 1.5rem; }
    .hero {
        background: linear-gradient(120deg, #172554, #1d4ed8);
        border-radius: 20px;
        color: white;
        margin-bottom: .8rem;
        padding: 1.2rem 1.4rem;
    }
    .hero h1 { color: white; font-size: 2rem; margin: 0 0 .25rem; }
    .hero p { color: #dbeafe; font-size: 1rem; margin: 0; }
    h2, h3 { color: #172554; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def cached_books(path: str):
    return load_books(path)


st.markdown(
    """
    <div class="hero">
        <h1>Catalog Insight</h1>
        <p>
            Public product data, cleaned and delivered as useful
            client-ready outputs.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

database_path = st.sidebar.text_input(
    "SQLite database",
    value=str(DEFAULT_DATABASE),
)
if st.sidebar.button("Reload data", width="stretch"):
    st.cache_data.clear()

books = cached_books(database_path)
if books.empty:
    st.info(
        "No data is available yet. Run "
        "`python run_pipeline.py --max-pages 3` and reload this page."
    )
    st.stop()

st.sidebar.subheader("Explore records")
search = st.sidebar.text_input("Search title or description")
all_categories = sorted(books["category"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Categories",
    options=all_categories,
    default=[],
    placeholder="All categories",
)
minimum_rating = st.sidebar.slider("Minimum rating", 0, 5, 0)
minimum_price = float(books["price_gbp"].min())
maximum_price = float(books["price_gbp"].max())
selected_price = st.sidebar.slider(
    "Price range (£)",
    min_value=minimum_price,
    max_value=maximum_price,
    value=(minimum_price, maximum_price),
)

filtered = filter_books(
    books,
    search=search,
    categories=selected_categories,
    minimum_rating=minimum_rating,
    price_range=selected_price,
)

latest_scrape = str(books["scraped_at"].max()).replace("T", " ")
st.sidebar.caption(f"Latest collection: {latest_scrape}")

overview_tab, products_tab, quality_tab, export_tab = st.tabs(
    ["Overview", "Products", "Quality", "Export"]
)

with overview_tab:
    metric_columns = st.columns(4)
    metric_columns[0].metric("Products", f"{len(filtered):,}")
    metric_columns[1].metric(
        "Average price",
        f"£{filtered['price_gbp'].mean():.2f}" if not filtered.empty else "—",
    )
    metric_columns[2].metric(
        "Categories",
        str(filtered["category"].nunique()) if not filtered.empty else "0",
    )
    metric_columns[3].metric(
        "Average rating",
        f"{filtered['rating'].mean():.1f} / 5" if not filtered.empty else "—",
    )

    if filtered.empty:
        st.info("No records match the current filters.")
    else:
        left, right = st.columns((3, 2))
        with left:
            st.subheader("Average price by category")
            category_summary = (
                filtered.groupby("category", as_index=False)["price_gbp"]
                .mean()
                .sort_values("price_gbp", ascending=False)
                .head(12)
                .set_index("category")
            )
            st.bar_chart(category_summary, color="#2563eb")

        with right:
            st.subheader("Rating distribution")
            rating_summary = (
                filtered["rating"].value_counts().sort_index().rename("products")
            )
            st.bar_chart(rating_summary, color="#38bdf8")

with products_tab:
    st.subheader("Collected product records")
    st.caption(
        f"Showing {len(filtered):,} of {len(books):,} products after filtering."
    )
    display_columns = [
        "title",
        "category",
        "rating",
        "price_gbp",
        "stock_count",
        "product_url",
    ]
    st.dataframe(
        filtered[display_columns],
        width="stretch",
        hide_index=True,
        column_config={
            "price_gbp": st.column_config.NumberColumn("Price", format="£%.2f"),
            "product_url": st.column_config.LinkColumn("Product"),
        },
    )
    st.download_button(
        "Download filtered CSV",
        data=protect_tabular_text(filtered)
        .to_csv(index=False)
        .encode("utf-8-sig"),
        file_name="filtered_books.csv",
        mime="text/csv",
    )

with quality_tab:
    quality = assess_data_quality(books)
    passed_checks = int(quality["Status"].eq("Passed").sum())
    issue_count = int(quality["Issues"].sum())
    quality_columns = st.columns(3)
    quality_columns[0].metric("Checks passed", f"{passed_checks} / {len(quality)}")
    quality_columns[1].metric("Issues found", str(issue_count))
    quality_columns[2].metric(
        "Product ID coverage",
        f"{books['source_id'].notna().mean():.0%}",
    )
    if issue_count == 0:
        st.success("All automated delivery checks passed.")
    else:
        st.warning("Some records need review before delivery.")
    st.dataframe(
        quality,
        width="stretch",
        hide_index=True,
        column_config={
            "Issues": st.column_config.NumberColumn("Issues", format="%d"),
        },
    )
    st.caption(
        "Checks cover required fields, duplicate identifiers and URLs, "
        "non-negative prices, and ratings within the expected range."
    )

with export_tab:
    left, right = st.columns((3, 2))
    with left:
        st.subheader("Delivery workflow")
        st.code(
            "Catalog pages\n"
            "  → product detail pages\n"
            "  → normalize and validate\n"
            "  → deduplicate\n"
            "  → SQLite + JSONL\n"
            "  → formatted Excel report",
            language="text",
        )
        st.info(
            "This demo uses a public practice website. Adapting the workflow "
            "to another catalog requires a review of its terms, robots.txt, "
            "rate limits, and data-use restrictions."
        )
    with right:
        st.subheader("Client-ready files")
        report_path = Path(database_path).with_name("books_report.xlsx")
        if report_path.exists():
            st.download_button(
                "Download full Excel report",
                data=report_path.read_bytes(),
                file_name=report_path.name,
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                width="stretch",
            )
        else:
            st.warning("Run the full pipeline to generate the Excel report.")
        st.download_button(
            "Download all records as CSV",
            data=protect_tabular_text(books)
            .to_csv(index=False)
            .encode("utf-8-sig"),
            file_name="all_books.csv",
            mime="text/csv",
            width="stretch",
        )
