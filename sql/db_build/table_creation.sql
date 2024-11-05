-- Create 'inputs' schema if it does not exist
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'inputs')
BEGIN
    EXEC('CREATE SCHEMA inputs')
END

-- Create 'outputs' schema if it does not exist
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'outputs')
BEGIN
    EXEC('CREATE SCHEMA outputs')
END
GO

-- Create 'metadata' schema if it does not exist
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'metadata')
BEGIN
    EXEC('CREATE SCHEMA metadata')
END
GO

-- Create Table 'metadata.ccm_run'
CREATE TABLE metadata.ccm_run (
    run_id INT PRIMARY KEY,
    [user] NVARCHAR(100) NOT NULL, 
    date DATETIME NOT NULL,
    version NVARCHAR(50) NOT NULL,
    comments NVARCHAR(200),  -- Allows NULL by default
    loaded BIT NOT NULL
) WITH (DATA_COMPRESSION = PAGE);
GO


-- Create Table 'outputs.components' 
CREATE TABLE outputs.ccm_components (
    run_id INT,
    year INT NOT NULL,
    race NVARCHAR(150),
    sex NVARCHAR(5),
    age INT,
    deaths INT,
    births INT,
    ins INT,
    outs INT,
);
GO


-- Create Table 'outputs.ccm_population'
CREATE TABLE outputs.ccm_population (
    year INT NOT NULL,
    race NVARCHAR(150),
    sex NVARCHAR(3),
    age INT,
    pop INT,
    pop_mil INT,
    gq INT,
    hh INT,
    hh_head_lf INT,
    child1 INT,
    senior1 INT,
    size1 INT,
    size2 INT,
    size3 INT,
    workers0 INT,
    workers1 INT,
    workers2 INT,
    workers3 INT,
) WITH (DATA_COMPRESSION = PAGE);
GO

-- Create Table 'outputs.rates'
CREATE TABLE outputs.ccm_rates (
    year INT NOT NULL,
    race NVARCHAR(150),
    sex NVARCHAR(3),
    age INT,
    rate_birth FLOAT,
    rate_death FLOAT,
    rate_in FLOAT,
    rate_out FLOAT,
    rate_gq FLOAT,
    rate_hh FLOAT,
    rate_hh_head_lf FLOAT,
    rate_size1 FLOAT,
    rate_size2 FLOAT,
    rate_size3 FLOAT,
    rate_workers0 FLOAT,
    rate_workers1 FLOAT,
    rate_workers2 FLOAT,
    rate_workers3 FLOAT,
) WITH (DATA_COMPRESSION = PAGE);
GO
