using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;

namespace DotnetWebApi.Data
{
    public class NameContext : DbContext
    {
        /// <summary>
        /// Constructor without params
        /// </summary>
        public NameContext()
            : base() 
        {

        }
        /// <summary>
        /// Constructor with options
        /// </summary>
        /// <param name="options"></param>
        public NameContext(DbContextOptions<NameContext> options)
            : base(options)
        {
        }
        /// <summary>
        /// Override Model Create
        /// </summary>
        /// <param name="builder"></param>
        protected override void OnModelCreating(ModelBuilder builder)
        {
            base.OnModelCreating(builder);
        }
    }
}