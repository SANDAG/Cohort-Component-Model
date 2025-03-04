import pandas as pd
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
#import plotly.plotly as py
import plotly.graph_objs as go
import plotly.express as px
import seaborn as sns

# Setting up tabs
tab1, tab2, tab3 = st.tabs(["Components", "Population","Rates"])

with tab1:
    st.title("Components of Change")
    comp_df = pd.read_csv('../output/components.csv')
    comp_df['year'] = comp_df['year'].astype('str')

    comp_cols = ['deaths', 'births', 'ins', 'outs']
    df_grouped = comp_df.groupby('year')[comp_cols].sum().reset_index()
    df_grouped['net_migration'] = df_grouped['ins'] - df_grouped['outs']

    st.write('''Births, Deaths, and Net Migration by year, San Diego County''')

    # Create the spline plot using Plotly
    fig = px.line(df_grouped, 
              x='year', 
              y=['deaths', 'births', 'net_migration'], 
              title=f'Births, Deaths, and Net Migration of San Diego County',
              labels={'year': 'Year', 'value': 'Value'},
              line_shape='spline')  # Spline for smooth curves

    # Show the plot
    st.plotly_chart(fig)
    st.write(df_grouped)


with tab2:
    st.title("Population Pyramid")
    pop_df = pd.read_csv("../output/population.csv")
    y_pop = st.slider("Pick a year", 2020, 2050, key='tab2')
    pop_yr_df = pop_df[pop_df['year'] == y_pop]
    df_grouped = pop_yr_df.groupby(['year', 'sex', 'age'])['pop'].sum().reset_index()
    # Age groups mapping
    age_bins = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, np.inf]
    age_labels = ['00-04', '05-09', '10-14', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', 
              '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '85+']
    df_grouped['agegroup'] = pd.cut(df_grouped['age'], bins=age_bins, labels=age_labels, right=True, include_lowest=True)

    temp = pd.pivot_table(df_grouped, index='agegroup', columns='sex', values='pop', aggfunc="sum")
    temp.columns = [f'pop_{i}' for i in temp.columns]
    temp = temp.reset_index()

    layout = go.Layout(
                    yaxis=go.layout.YAxis(
                        range=[-5, 90],
                        tickvals=age_bins[:-1],
                        ticktext=age_labels,
                        title='Age'),
                    xaxis=go.layout.XAxis(
                        range=[-140000, 140000],
                        tickvals=[-140000, -120000, -100000, -80000, -60000, -40000, -20000, 0, 
                                  20000, 40000, 60000, 80000, 100000, 120000, 140000],
                        ticktext=[140000, 120000, 100000, 80000, 60000, 40000, 20000, 0, 
                                  20000, 40000, 60000, 80000, 100000, 120000, 140000],
                        title='Population'),
                    barmode='overlay',
                    bargap=0.1)
    
    mens_bins = temp['pop_M'].values
    womens_bins = -1*temp['pop_F'].values

    data = [go.Bar(y=age_bins,
                x=mens_bins,
                orientation='h',
                name='Men',
                hoverinfo='x',
                marker=dict(color='cornflowerblue')
                ),
            go.Bar(y=age_bins,
                x=womens_bins,
                orientation='h',
                name='Women',
                text=-1 * womens_bins.astype('int'),
                hoverinfo='text',
                marker=dict(color='indianred')
                )]
    
    st.plotly_chart(dict(data=data, layout=layout))

    race_df = 100*pop_yr_df.groupby(['race'])['pop'].sum() / pop_yr_df['pop'].sum()
    race_df.name = 'percent'
    race_df = race_df.reset_index()
    race_df['Race'] = 'Race'
    #st.bar_chart(race_df, x='Race', y='percent', color='race', horizontal=True)
    
    fig = px.pie(
        race_df,
        values="percent",
        names="race",
        title=f"Ethnicity/Race proportions",
        hole=0.3
    )
    st.plotly_chart(fig)


# Function to calculate Life Expectancy at Age 0 (birth) by cohort
def calculate_life_expectancy_age_0_by_cohort(df, rate_col):
    # Initialize an empty list to store life expectancy for each cohort
    life_expectancy_list = []

    
    for sex in df['sex'].unique():
        for race in df['race'].unique():
            for year in df['year'].unique():
                # Filter data for race and sex
                df_cohort = df[(df['sex'] == sex) & (df['race'] == race) & (df['year'] == year)].copy()
                df_cohort = df_cohort.sort_values(by='age')
                
                # Initialize survivors at age 0 (starting cohort of 100,000)
                l_x = [100000]
                total_persons_years_lived = 0
                
                # Calculate the number of survivors and total years lived for each age
                for i, row in df_cohort.iterrows():
                    # Calculate survival probability: p_x = 1 - q_x
                    q_x = row[rate_col]
                    p_x = 1 - q_x
                    
                    deaths = l_x[-1] * q_x
                    survives = l_x[-1] * p_x

                    # Calculate survivors at age x
                    l_x.append( survives + 0.5 * deaths)
                    
                    # Add total years lived
                    total_persons_years_lived += l_x[-1]
                
                # Calculate Life Expectancy at Age 0 (e_0)
                life_expectancy_age_0 = total_persons_years_lived / l_x[0]
                
                # Append the result to the life expectancy
                life_expectancy_list.append({
                    'year': year,
                    'sex': sex,
                    'race': race,
                    'life_expectancy_at_birth': life_expectancy_age_0
                })

    # Convert the life expectancy list to a DataFrame
    life_expectancy_df = pd.DataFrame(life_expectancy_list)
    return life_expectancy_df


def calculate_life_expectancy_age_0_by_sex(df, rate_col):
    life_expectancy_list = []

    
    for sex in df['sex'].unique():
        for year in df['year'].unique():
            # Filter data for race and sex
            df_cohort = df[(df['sex'] == sex) & (df['year'] == year)].copy()
            df_cohort = df_cohort.sort_values(by='age')
            
            
            l_x = [100000]
            total_persons_years_lived = 0
            
            # Calculate the number of survivors and total years lived for each age
            for i, row in df_cohort.iterrows():
                # Calculate survival probability: p_x = 1 - q_x
                q_x = row[rate_col]
                p_x = 1 - q_x
                
                deaths = l_x[-1] * q_x
                survives = l_x[-1] * p_x

                # Calculate survivors at age x
                l_x.append( survives + 0.5 * deaths)
                
                # Add total years lived (survivors at each age * 1 year of life expectancy)
                total_persons_years_lived += l_x[-1]
            
            # Calculate Life Expectancy at Age 0 (e_0)
            life_expectancy_age_0 = total_persons_years_lived / l_x[0]
            
            # Append the result to the life expectancy
            life_expectancy_list.append({
                'year': year,
                'sex': sex,
                'life_expectancy_at_birth': life_expectancy_age_0
            })

    # Convert the life expectancy list to a DataFrame
    life_expectancy_df = pd.DataFrame(life_expectancy_list)
    return life_expectancy_df


with tab3:
    # Create the Streamlit app
    st.title("Life Expectancy and TFR Analysis")

    # Dropdown to select the category
    categories = ["Total Fertility Rate (TFR)", "Life Expectancy M1", "Life Expectancy M2"]
    category = st.selectbox("Pick a category to analyze", categories)

    # Reading data
    population_df = pd.read_csv("../output/population.csv")
    component_df = pd.read_csv("../output/components.csv")
    rates_df = pd.read_csv('../output/rates.csv')

    # TFR
    if category == "Total Fertility Rate (TFR)":
        
        def calculate_tfr_by_race(df):
            tfr_df_race = df.groupby(['year', 'race'])['rate_birth'].sum().reset_index()
            return tfr_df_race

        tfr_df_race = calculate_tfr_by_race(rates_df)
        fig4 = px.line(tfr_df_race, x='year', y='rate_birth', color='race',
                    title="Total Fertility Rate (TFR) by Year and Race/Ethnicity",
                    labels={"rate_birth": "Total Fertility Rate (TFR)", "year": "Year"},
                    markers=True)
        st.plotly_chart(fig4, use_container_width=True)
        

        # Display the firtility rates per year
        y_tfr = st.slider("Pick a year", 2020, 2050, key='tab3_tfr')
        df = tfr_df_race[tfr_df_race['year'] == y_tfr].copy()
        df['year'] = df['year'].astype('object')
        st.write("Total Fertility Rate (TFR) Data (by Year and Race/Ethnicity)")
        st.dataframe(df.style.format({
            'year': lambda x: f"{x:.0f}",
            'rate_birth': lambda x: f"{x:.3f}"}), hide_index=True)

    elif category == "Life Expectancy -- Population projections and deaths output by the model":
        # Merging population and death data for method 1
        population_df = pd.read_csv("../output/population.csv")
        component_df = pd.read_csv("../output/components.csv")
        merged_df = pd.merge(population_df, component_df, on=['year', 'sex', 'race', 'age'])
        merged_df = merged_df.groupby(['age', 'sex', 'year'])[['pop', 'deaths']].sum().reset_index()
        temp_df = merged_df.groupby(['age', 'year'])[['pop', 'deaths']].sum().reset_index()
        temp_df['sex'] = 'All'
        final_df = pd.concat([merged_df, temp_df[merged_df.columns]])

        # Calculate the Population to Death Ratio for Population Projections and Deaths method
        final_df['death_pop_ratio'] = np.where(final_df['pop'] == 0, 0, final_df['deaths'] / final_df['pop'])
        life_expectancy_df = calculate_life_expectancy_age_0_by_sex(final_df, 'death_pop_ratio')

        # Plot the Life Expectancy Population Projections and Deaths
        fig1 = px.line(life_expectancy_df, x='year', y='life_expectancy_at_birth', color='sex',
                    title="Life Expectancy at Birth by Cohort",
                    labels={"life_expectancy_at_birth": "Life Expectancy at Birth", "year": "Year"},
                    markers=True)
        st.plotly_chart(fig1, use_container_width=True)
        
        # Life exp dataframe
        y_m1 = st.slider("Pick a year", 2020, 2050, key='tab3_m1')
        df = life_expectancy_df[life_expectancy_df['year'] == y_m1].copy()
        df['year'] = df['year'].astype('object')
        st.write("Life Expectancy by Population Projections and Deaths")
        st.dataframe(df.style.format({
            'year': lambda x: f"{x:.0f}",
            'life_expectancy_at_birth': lambda x: f"{x:.2f}"}
            ), hide_index=True)


    elif category == "Life Expectancy - Mortality Rates":

        # Calculate Life Expectancy for Mortality Rates method
        life_expectancy_df = calculate_life_expectancy_age_0_by_cohort(rates_df, 'rate_death')

        # Plot the Life Expectancy Mortality Rates method
        sex = st.radio("Sex", life_expectancy_df['sex'].unique(), key='M2')
        lifeExp_filter = life_expectancy_df[(life_expectancy_df['sex'] == sex)]
        fig1 = px.line(lifeExp_filter, x='year', y='life_expectancy_at_birth', color='race',
                    title="Life Expectancy at Birth by Cohort (M2)",
                    labels={"life_expectancy_at_birth": "Life Expectancy at Birth", "year": "Year"},
                    markers=True)
        st.plotly_chart(fig1, use_container_width=True)
        
        #Life exp table by cohort
        y_m2 = st.slider("Pick a year", 2020, 2050, key='tab3_m2')
        df = life_expectancy_df[life_expectancy_df['year'] == y_m2].copy()
        df['year'] = df['year'].astype('object')
        
        st.write("Life Expectancy by Mortality Rates")
        st.dataframe(df.style.format({
            'year': lambda x: f"{x:.0f}",
            'life_expectancy_at_birth': lambda x: f"{x:.2f}"}
            ), hide_index=True)