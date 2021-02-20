from .main import Football


def setup(bot):
    bot.add_cog(Football(bot))
