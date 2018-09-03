using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;

//& region (logging)
using Microsoft.Extensions.Logging;
//& region (logging:serilog)
using Serilog;
using Serilog.Events;
using Serilog.Sinks.SystemConsole.Themes;
//& end (logging:serilog)
//& end (logging)  

namespace DotnetWebApi
{
    public class Program
    {
        public static void Main(string[] args)
        {
//& region (logging)
    //& region (logging:serilog)
            Log.Logger = new LoggerConfiguration()
                .MinimumLevel.Debug()
                .MinimumLevel.Override("Microsoft", LogEventLevel.Warning)
                .MinimumLevel.Override("System", LogEventLevel.Warning)
                .Enrich.FromLogContext()
                .WriteTo.File(@"logs.txt")
                .WriteTo.Console(outputTemplate: "[{Timestamp:HH:mm:ss} {Level}] {SourceContext}{NewLine}{Message:lj}{NewLine}{Exception}{NewLine}", theme: AnsiConsoleTheme.Literate)
                .CreateLogger();
    //& end (logging:serilog)
//& end (logging)            
            CreateWebHostBuilder(args).Build().Run();
        }
        public static IWebHostBuilder CreateWebHostBuilder(string[] args) =>
            WebHost.CreateDefaultBuilder(args)
//& region (logging)
    //& region (logging:serilog)
                .ConfigureLogging(builder =>
                    {
                        builder.ClearProviders();
                        builder.AddSerilog();
                    })
    //& end (logging:serilog)
//& end (logging)
                .UseStartup<Startup>();
                
    }
}
