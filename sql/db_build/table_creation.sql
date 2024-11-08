-- Create 'outputs' schema if it does not exist
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'outputs')
BEGIN
    EXEC('CREATE [SCHEMA] [outputs]')
END
GO

-- Create 'metadata' schema if it does not exist
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'metadata')
BEGIN
    EXEC('CREATE [SCHEMA] [metadata]')
END
GO

-- Create Table 'metadata.run'
CREATE TABLE [metadata].[run]
(
    [run_id] INT PRIMARY KEY,
    [user] NVARCHAR(100) NOT NULL,
    [date] DATETIME NOT NULL,
    [version] NVARCHAR(50) NOT NULL,
    [comments] NVARCHAR(200),  -- Allows NULL by default
    [loaded] BIT NOT NULL
) WITH (DATA_COMPRESSION = PAGE);
GO


-- Create Table 'outputs.components'
CREATE TABLE [outputs].[components]
(
    [run_id] INT,
    [year] INT NOT NULL,
    [race] NVARCHAR(150),
    [sex] NVARCHAR(5),
    [age] INT,
    [deaths] INT,
    [births] INT,
    [ins] INT,
    [outs] INT,
    INDEX ccsi_components CLUSTERED COLUMNSTORE,
    CONSTRAINT ixuq_components UNIQUE ([run_id], [year], [race], [sex], [age]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT fk_components_run FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id])
)
GO


-- Create Table 'outputs.population'
CREATE TABLE [outputs].[population]
(
    [run_id] INT,
    [year] INT NOT NULL,
    [race] NVARCHAR(150),
    [sex] NVARCHAR(3),
    [age] INT,
    [pop] INT,
    [pop_mil] INT,
    [gq] INT,
    [hh] INT,
    [hh_head_lf] INT,
    [child1] INT,
    [senior1] INT,
    [size1] INT,
    [size2] INT,
    [size3] INT,
    [workers0] INT,
    [workers1] INT,
    [workers2] INT,
    [workers3] INT,
    INDEX ccsi_population CLUSTERED COLUMNSTORE,
    CONSTRAINT ixuq_population UNIQUE ([run_id], [year], [race], [sex], [age]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT fk_population_run FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id])
)
GO


-- Create Table 'outputs.rates'
CREATE TABLE [outputs].[rates]
(
    [run_id] INT,
    [year] INT NOT NULL,
    [race] NVARCHAR(150),
    [sex] NVARCHAR(3),
    [age] INT,
    [rate_birth] FLOAT,
    [rate_death] FLOAT,
    [rate_in] FLOAT,
    [rate_out] FLOAT,
    [rate_gq] FLOAT,
    [rate_hh] FLOAT,
    [rate_hh_head_lf] FLOAT,
    [rate_size1] FLOAT,
    [rate_size2] FLOAT,
    [rate_size3] FLOAT,
    [rate_workers0] FLOAT,
    [rate_workers1] FLOAT,
    [rate_workers2] FLOAT,
    [rate_workers3] FLOAT,
    INDEX ccsi_rates CLUSTERED COLUMNSTORE,
    CONSTRAINT ixuq_rates UNIQUE ([run_id], [year], [race], [sex], [age]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT fk_rates_run FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id])
)
GO