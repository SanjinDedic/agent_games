import React from 'react';

import { imageUrl, videoUrl } from '../config/assets';

const About = () => {
  return (
    <div className="min-h-screen bg-ui-lighter pt-12">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-league-blue to-primary py-20">
        <div className="container mx-auto px-6 text-center">
          <h1 className="text-4xl md:text-6xl font-bold text-white mb-6">
            About Agent Games
          </h1>
          <p className="text-xl text-league-text max-w-3xl mx-auto">
            The story behind the platform — and how you can try it yourself.
          </p>
        </div>
      </section>

      {/* Story Section */}
      <section className="py-16">
        <div className="container mx-auto px-6">
          <div className="max-w-xl mx-auto grid grid-cols-2 gap-4 mb-10">
            <img
              src={imageUrl('about/vcc1.jpeg')}
              alt=""
              className="w-full h-auto rounded-lg shadow-md object-cover"
            />
            <img
              src={imageUrl('about/vcc2.jpeg')}
              alt=""
              className="w-full h-auto rounded-lg shadow-md object-cover"
            />
          </div>
          <div className="max-w-3xl mx-auto space-y-5 text-ui text-lg leading-relaxed">
            <p>
              Hi — I'm Sanjin, a Python developer and a recovering computer
              science teacher.
            </p>
            <p>
              Agent Games is an experiment that hatched out of the{' '}
              <strong>Victorian Coding Challenge</strong>. It's been a labour
              of love for four years, and somewhere along the way I had so
              much fun building it that I decided to move into programming
              full time.
            </p>
            <p>
              Every year over <strong>1,000 students</strong> take part, and
              every game you see here was designed for the Victorian Coding
              Challenge itself.
            </p>
            <p>
              My goal from here is to get Agent Games into more universities
              and high schools running extension programs — anywhere curious
              students are learning to think algorithmically.
            </p>
            <p>
              I'm always looking for collaborators. If you have ideas for
              making the site better or more secure, or you'd like to design a
              new game for the platform — <strong>get in touch</strong>.
            </p>
            <p>
              There's nothing for sale here. This is, and will remain, free to
              use.
            </p>
          </div>
        </div>
      </section>

      {/* Tutorial Section */}
      <section className="py-16 bg-white">
        <div className="container mx-auto px-6">
          <h2 className="text-3xl font-bold text-ui-dark text-center mb-12">
            Tutorial
          </h2>
          <div className="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto">
            {/* About Agent Games */}
            <div className="bg-ui-lighter rounded-lg shadow-md overflow-hidden flex flex-col">
              <div className="aspect-video bg-black">
                <video
                  controls
                  preload="metadata"
                  className="w-full h-full"
                  src={videoUrl('about_agent_games.mp4')}
                />
              </div>
              <div className="p-4">
                <h3 className="text-xl font-semibold text-ui-dark mb-1">
                  About Agent Games
                </h3>
                <p className="text-ui text-sm">
                  A short overview of what the platform does and who it's for.
                </p>
              </div>
            </div>

            {/* Run Locally */}
            <div className="bg-ui-lighter rounded-lg shadow-md overflow-hidden flex flex-col">
              <div className="aspect-video bg-black">
                <video
                  controls
                  preload="metadata"
                  className="w-full h-full"
                  src={videoUrl('run_locally.mp4')}
                />
              </div>
              <div className="p-4">
                <h3 className="text-xl font-semibold text-ui-dark mb-1">
                  Run Locally in 5 min!
                </h3>
                <p className="text-ui text-sm">
                  Walk-through of running Agent Games on your own machine.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pycon Presentation Section */}
      <section className="py-16 bg-ui-lighter">
        <div className="container mx-auto px-6">
          <h2 className="text-3xl font-bold text-ui-dark text-center mb-12">
            Pycon Presentation
          </h2>
          <div className="max-w-3xl mx-auto">
            <div className="bg-white rounded-lg shadow-md overflow-hidden flex flex-col">
              <div className="aspect-video bg-black">
                <iframe
                  className="w-full h-full border-0"
                  src="https://www.youtube.com/embed/GhwYsMxbvkQ"
                  title="Pycon Presentation"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
              <div className="p-4">
                <h3 className="text-xl font-semibold text-ui-dark mb-1">
                  Pycon Presentation
                </h3>
                <p className="text-ui text-sm">
                  Agent Games presented live at PyCon AU — the vision and the
                  classroom results.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default About;
